"""Punto di ingresso: genera e invia la rassegna stampa quotidiana.

Esecuzione:
    python main.py            # raccoglie, riassume e invia la mail
    python main.py --dry-run  # come sopra, ma salva l'HTML in out/ senza inviare

La schedulazione avviene tramite GitHub Actions (vedi .github/workflows).
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from typing import List

import config
from src import sources
from src.email_builder import build_email
from src.fetchers.rss import fetch_rss
from src.fetchers.scraper import fetch_scrape
from src.mailer import send_email
from src.models import Article, SourceResult
from src.summarizer import summarize


def _log(msg: str) -> None:
    now = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{now}] {msg}", flush=True)


def _schedule_guard() -> bool:
    """Evita invii doppi con il cambio ora legale/solare.

    Il workflow GitHub gira due volte (per coprire CET e CEST): questa guardia
    fa proseguire solo l'esecuzione che, in ora italiana, cade nell'ora
    prevista (7). Le esecuzioni manuali (workflow_dispatch) o locali passano
    sempre.
    """
    if os.getenv("GITHUB_EVENT_NAME") != "schedule":
        return True
    local_hour = datetime.now(config.TIMEZONE).hour
    if local_hour == config.TARGET_HOUR:
        return True
    _log(
        f"Esecuzione pianificata alle {local_hour}:xx ora italiana, "
        f"diversa dalle {config.TARGET_HOUR}:10 previste. Salto."
    )
    return False


def _collect_source(source: dict) -> SourceResult:
    """Raccoglie gli articoli di una fonte, gestendo gli errori."""
    name = source["nome"]
    category = source["categoria"]
    result = SourceResult(name=name, category=category)

    try:
        articles: List[Article] = []
        if source.get("rss_disponibile") and source.get("rss_url"):
            articles = fetch_rss(source)
            # Le "pagine hub" (Sole, ICE, ISTAT) non sono feed veri: se il
            # feed non restituisce nulla, ripieghiamo sullo scraping.
            if not articles:
                _log(f"  {name}: feed vuoto, provo lo scraping…")
                articles = fetch_scrape(source)
        else:
            articles = fetch_scrape(source)

        result.articles = _postprocess(articles)
        _log(f"  {name}: {len(result.articles)} articoli")
    except Exception as exc:  # isoliamo l'errore per non fermare la rassegna
        result.error = f"{type(exc).__name__}: {exc}"
        _log(f"  {name}: ERRORE — {result.error}")

    return result


def _postprocess(articles: List[Article]) -> List[Article]:
    """Filtra per data, rimuove i duplicati e applica il tetto per fonte."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=config.RECENCY_HOURS)

    seen_urls = set()
    kept: List[Article] = []
    for art in articles:
        if not art.url or art.url in seen_urls:
            continue
        # Teniamo gli articoli recenti; quelli senza data li teniamo comunque
        # (best effort: spesso lo scraping non recupera la data).
        if art.published is not None:
            published = art.published
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
            if published < cutoff:
                continue
        seen_urls.add(art.url)
        kept.append(art)
        if len(kept) >= config.MAX_ARTICLES_PER_SOURCE:
            break
    return kept


def main() -> int:
    dry_run = "--dry-run" in sys.argv

    if not _schedule_guard():
        return 0

    _log("Avvio raccolta fonti…")
    fonti = sources.load_sources()
    results = [_collect_source(src) for src in fonti]

    total = sum(len(r.articles) for r in results)
    _log(f"Raccolti {total} articoli in totale. Genero i riassunti…")

    for result in results:
        for article in result.articles:
            try:
                article.summary = summarize(article)
            except Exception as exc:
                article.summary = f"(Riassunto non disponibile: {exc})"
                _log(f"  Riassunto fallito per «{article.title[:60]}»: {exc}")

    subject, html, text = build_email(results)

    if dry_run:
        os.makedirs("out", exist_ok=True)
        with open("out/rassegna.html", "w", encoding="utf-8") as fh:
            fh.write(html)
        _log(f"[DRY-RUN] Oggetto: {subject}")
        _log("[DRY-RUN] Anteprima salvata in out/rassegna.html (nessun invio).")
        return 0

    if total == 0:
        _log("Nessun articolo: invio comunque una mail di riepilogo.")

    send_email(subject, html, text)
    _log(f"Mail inviata a {config.MAIL_TO}. Oggetto: {subject}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
