# Rassegna stampa quotidiana automatica

Legge una serie di fonti (economia d'impresa, economia reale,
internazionalizzazione, innovazione, Made in Italy), raccoglie gli articoli
delle ultime ore, ne genera un **riassunto di ~4 righe** con Claude e invia
tutto via email **ogni mattina alle 7:10** (ora italiana).

## Come funziona

```
fonti (JSON) ──► raccolta (RSS + scraping) ──► riassunti (Claude Haiku)
             ──► impaginazione mail (HTML) ──► invio (Resend)
```

La schedulazione gira gratuitamente su **GitHub Actions**: non serve tenere il
computer acceso.

## Struttura del progetto

| File / cartella | Cosa fa |
|---|---|
| `fonti_rassegna_stampa_economia_impresa.json` | Elenco delle fonti |
| `config.py` | Parametri (orario, limiti, modello, ecc.) |
| `main.py` | Orchestrazione: raccolta → riassunti → mail |
| `src/fetchers/rss.py` | Lettura dei feed RSS |
| `src/fetchers/scraper.py` | Scraping delle fonti senza RSS |
| `src/fetchers/extractor.py` | Estrazione del testo integrale di un articolo |
| `src/summarizer.py` | Riassunti tramite l'API di Anthropic |
| `src/email_builder.py` | Composizione della mail (HTML + testo) |
| `src/mailer.py` | Invio via Resend |
| `.github/workflows/rassegna.yml` | Schedulazione giornaliera |

## Fonti: cosa aspettarsi

- **5 fonti con RSS verificato** (Il Sole 24 Ore, Pambianconews,
  FashionNetwork Italia, Agenzia ICE, ISTAT): affidabili.
- **8 fonti senza RSS**: recuperate via scraping, con risultati variabili. Le
  testate a pagamento (Milano Finanza, Italia Oggi, MF Fashion) potrebbero
  fornire solo titoli/anteprime, non il testo integrale. Se una fonte non
  restituisce nulla, la mail lo segnala in fondo e prosegue con le altre.

## Prova in locale (facoltativa)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # poi inserisci le tue chiavi nel file .env
python main.py --dry-run    # genera out/rassegna.html senza inviare la mail
```

## Messa in produzione

1. Crea le chiavi API (Anthropic e Resend) e un repository GitHub.
2. In GitHub: **Settings → Secrets and variables → Actions** e aggiungi:
   `ANTHROPIC_API_KEY`, `RESEND_API_KEY`, `MAIL_FROM`, `MAIL_TO`.
3. Il workflow parte da solo ogni mattina; puoi anche lanciarlo a mano da
   **Actions → Rassegna Stampa → Run workflow**.

## Costi indicativi

- **API Claude**: ~1–3 €/mese (modello Haiku, il più economico).
- **Resend** e **GitHub Actions**: piani gratuiti, sufficienti per un invio
  al giorno.

## Note

- I riassunti sono generati da un modello linguistico: utili come sintesi, ma
  vanno verificati prima di ogni uso professionale.
- Per usare un mittente personalizzato (invece di `onboarding@resend.dev`)
  occorre verificare un dominio su Resend.
