# Kit Watch — Generalisierter Preis-Monitor

**Date:** 2026-03-26
**Status:** Draft
**Author:** Paul Fiedler + Claude

---

## 1. Vision

Ein generalisiertes CLI-Tool zum Ueberwachen von Preisen auf beliebigen Plattformen. Kein Claude-API-Call noetig fuer den Scan selbst — rein mechanisch, kostenguenstig, laeuft 24/7.

```
kit watch add "MacBook Pro M4 Pro 48GB" --source apple-refurb,asgoodasnew,backmarket --below 2800
kit watch list
kit watch run              # einmal manuell scannen
kit watch run --daemon     # alle 15 min (konfigurierbar)
kit watch history          # Preisverlauf anzeigen
kit watch config           # Preislimits, Quellen, Notifications anpassen
```

---

## 2. Architektur

```
src/kit/watch/
├── core.py           # WatchJob, WatchResult, PriceHit (Pydantic models)
├── scrapers/
│   ├── base.py       # AbstractScraper — Interface fuer alle Quellen
│   ├── apple_refurb.py   # Apple Refurbished Store DE
│   ├── asgoodasnew.py    # asgoodasnew.com
│   ├── backmarket.py     # BackMarket DE
│   ├── rebuy.py          # rebuy.de
│   ├── amazon.py         # Amazon Warehouse DE
│   └── geizhals.py       # Geizhals.de Preisvergleich
├── notify.py         # Notification-System (macOS + iMessage)
├── storage.py        # SQLite fuer Preisverlauf + State
├── scheduler.py      # Daemon-Loop mit konfigurierbarem Intervall
└── commands.py       # CLI subcommands fuer "kit watch"
```

### Interfaces (wie alle Kit-Tools)

1. **CLI**: `kit watch add/list/run/history/config`
2. **Python API**: `from kit.watch import scan_all, add_job`
3. **MCP Server**: `kit_watch_add`, `kit_watch_scan`, `kit_watch_status`

---

## 3. Datenmodelle

```python
class WatchJob(BaseModel):
    """Ein Ueberwachungsauftrag."""
    id: str                         # UUID
    name: str                       # "MacBook Pro M4 Pro 48GB"
    keywords: list[str]             # ["MacBook Pro", "M4 Pro", "48GB"]
    exclude_keywords: list[str]     # ["Huelle", "Case", "Folie"]
    sources: list[str]              # ["apple-refurb", "asgoodasnew", ...]
    price_alerts: PriceAlerts
    active: bool = True
    created: datetime
    last_scanned: datetime | None = None

class PriceAlerts(BaseModel):
    """Konfigurierbare Preisschwellen."""
    instant: float | None = None    # SOFORT zuschlagen
    good_deal: float | None = None  # Guter Deal, anschauen
    worth_it: float | None = None   # Interessant
    currency: str = "EUR"

class PriceHit(BaseModel):
    """Ein gefundenes Angebot."""
    job_id: str
    source: str
    title: str                      # "MacBook Pro 14 M4 Pro 48GB 1TB Space Schwarz"
    price: float
    currency: str = "EUR"
    url: str
    condition: str                  # "refurbished", "wie_neu", "gebraucht", "neu"
    timestamp: datetime
    alert_level: str | None = None  # "instant", "good_deal", "worth_it", None

class ScanResult(BaseModel):
    """Ergebnis eines Scan-Durchlaufs."""
    job_id: str
    timestamp: datetime
    hits: list[PriceHit]
    errors: list[str]               # Fehlermeldungen pro Quelle
    duration_seconds: float
```

---

## 4. Scraper-Design

### Base Scraper Interface

```python
class AbstractScraper(ABC):
    """Jede Quelle implementiert dieses Interface."""

    name: str                       # "apple-refurb"
    display_name: str               # "Apple Refurbished DE"
    base_url: str

    @abstractmethod
    async def search(self, keywords: list[str], exclude: list[str]) -> list[RawListing]:
        """Suche nach Produkten. Gibt rohe Listings zurueck."""
        ...

    @abstractmethod
    def parse_listing(self, raw: RawListing) -> PriceHit | None:
        """Parse ein rohes Listing in ein PriceHit. None = nicht relevant."""
        ...
```

### Scraping-Strategie (kostenguenstig)

- **Kein Headless Browser** — nur `httpx` + `selectolax` (schneller als BeautifulSoup)
- **Respektvolle Rate Limits** — max 1 Request/Quelle pro Scan, random Delay 1-3s
- **User-Agent Rotation** — realistischer Browser UA
- **Caching** — identische Ergebnisse nicht doppelt notifizieren (SQLite State)
- **Kein Login noetig** — alle Quellen sind oeffentlich zugaenglich
- **Fallback**: Wenn Scraping blockiert wird → RSS/Atom Feed falls vorhanden, sonst Source deaktivieren + User informieren

### Robustheit

- Jeder Scraper ist unabhaengig — wenn einer fehlschlaegt, laufen die anderen weiter
- Strukturaenderungen auf Websites werden erkannt (erwartete Selektoren fehlen) → Warning statt Crash
- Retry mit exponential Backoff bei temporaeren Fehlern (429, 503)
- Health-Check: wenn ein Scraper 3x hintereinander keine Ergebnisse liefert → Warning

---

## 5. Notification-System

### macOS Native Notification

```python
# Via osascript — keine Dependencies noetig
def notify_macos(title: str, message: str, sound: str = "Hero") -> None:
    subprocess.run([
        "osascript", "-e",
        f'display notification "{message}" with title "{title}" sound name "{sound}"'
    ])
```

### iMessage

```python
# Via osascript — sendet an eigene Nummer/Email
def notify_imessage(recipient: str, message: str) -> None:
    subprocess.run([
        "osascript", "-e",
        f'''tell application "Messages"
            set targetService to 1st account whose service type = iMessage
            set targetBuddy to participant "{recipient}" of targetService
            send "{message}" to targetBuddy
        end tell'''
    ])
```

### Alert-Level Mapping

| Level | macOS Sound | iMessage | Wann |
|-------|------------|----------|------|
| `instant` | "Hero" (laut) | Ja, sofort | Preis < instant-Schwelle |
| `good_deal` | "Glass" | Ja | Preis < good_deal-Schwelle |
| `worth_it` | "Pop" (leise) | Nein | Preis < worth_it-Schwelle |

---

## 6. Storage (SQLite)

```sql
-- Persistent in ~/.cache/kit/watch.db

CREATE TABLE watch_jobs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    keywords TEXT NOT NULL,          -- JSON array
    exclude_keywords TEXT DEFAULT '[]',
    sources TEXT NOT NULL,            -- JSON array
    price_instant REAL,
    price_good_deal REAL,
    price_worth_it REAL,
    currency TEXT DEFAULT 'EUR',
    active INTEGER DEFAULT 1,
    created TEXT NOT NULL,
    last_scanned TEXT
);

CREATE TABLE price_hits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT REFERENCES watch_jobs(id),
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    price REAL NOT NULL,
    currency TEXT DEFAULT 'EUR',
    url TEXT NOT NULL,
    condition TEXT,
    alert_level TEXT,
    timestamp TEXT NOT NULL,
    notified INTEGER DEFAULT 0       -- Schon benachrichtigt?
);

CREATE TABLE scan_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT REFERENCES watch_jobs(id),
    timestamp TEXT NOT NULL,
    hits_count INTEGER,
    errors TEXT,                      -- JSON array
    duration_seconds REAL
);
```

Deduplizierung: Ein Hit wird nur notifiziert wenn `(source, url, price)` noch nicht in den letzten 24h gesehen wurde.

---

## 7. CLI Commands

```bash
# === Job Management ===
kit watch add "MacBook Pro M4 Pro 48GB" \
    --source apple-refurb,asgoodasnew,backmarket,rebuy,amazon,geizhals \
    --instant 2500 \
    --good-deal 2800 \
    --worth-it 3000 \
    --exclude "Huelle,Case,Folie,Schutz"

kit watch list                       # Alle aktiven Jobs anzeigen
kit watch edit <job-id>              # Job bearbeiten (interaktiv)
kit watch pause <job-id>             # Job pausieren
kit watch remove <job-id>            # Job loeschen

# === Scanning ===
kit watch run                        # Einmal alle aktiven Jobs scannen
kit watch run --job <id>             # Nur einen bestimmten Job scannen
kit watch run --daemon               # Daemon-Modus: alle 15 min scannen
kit watch run --daemon --interval 5  # Custom Intervall (Minuten)

# === History & Analytics ===
kit watch history                    # Letzte Hits anzeigen
kit watch history --job <id>         # Hits fuer einen Job
kit watch history --chart            # ASCII Preisverlauf
kit watch status                     # Health-Check aller Scraper

# === Config ===
kit watch config                     # Notification-Settings anzeigen/aendern
kit watch config --imessage "+49..."  # iMessage Empfaenger setzen
kit watch config --sound hero        # Default Sound aendern
```

---

## 8. MCP Server Tools

```python
# Neue Tools fuer Claude Code Integration
kit_watch_add       # Job anlegen (Claude kann das im Gespraech tun)
kit_watch_scan      # Einmal scannen und Ergebnisse zurueckgeben
kit_watch_status    # Aktive Jobs + letzte Hits
kit_watch_history   # Preisverlauf fuer einen Job
```

**Use Case**: Claude kann im Gespraech sagen "Ich richte dir einen Watch-Job ein" und direkt `kit_watch_add` aufrufen.

---

## 9. Daemon-Betrieb

### Lokal (macOS)

```bash
# Einfach: im Terminal laufen lassen
kit watch run --daemon --interval 15

# Robust: als launchd Service
# ~/Library/LaunchAgents/com.kit.watch.plist
```

### Remote (Hetzner VPS)

```bash
# systemd timer (wie andere Kit-Tasks)
# Notifications werden per API an den Mac weitergeleitet
# Alternative: Pushover/Ntfy.sh fuer Remote-Notifications
```

---

## 10. Kosten

| Komponente | Kosten |
|------------|--------|
| httpx + selectolax | 0€ (Open Source) |
| SQLite | 0€ (Built-in) |
| macOS Notifications | 0€ (osascript) |
| iMessage | 0€ (lokal via Messages.app) |
| Compute (lokal) | ~0€ (minimal CPU) |
| Compute (Hetzner) | In den ~15€/Monat VPS enthalten |
| **Gesamt** | **0€ zusaetzlich** |

---

## 11. Generalisierung

Das Tool ist absichtlich generisch gehalten:

- **Nicht nur MacBooks**: `kit watch add "Sony A7IV Body" --source amazon,geizhals --below 1500`
- **Nicht nur Hardware**: `kit watch add "Berlin Mitte 2-Zimmer" --source immoscout --below 800`
- **Neue Quellen**: Scraper-Interface ist einfach zu implementieren, ein neuer Scraper = eine neue Datei
- **Konfigurierbar**: Alle Schwellen, Quellen, Intervalle, Notifications sind pro Job einstellbar

---

## 12. Implementation Roadmap

### Phase 1 — MVP (jetzt)
- [ ] Core Models + SQLite Storage
- [ ] 2 Scraper: Apple Refurbished + asgoodasnew
- [ ] macOS Notification
- [ ] CLI: `add`, `list`, `run`
- [ ] Tests mit VCR Cassettes

### Phase 2 — Vollausbau
- [ ] Weitere Scraper: BackMarket, rebuy, Amazon, Geizhals
- [ ] iMessage Notification
- [ ] Daemon-Modus mit Intervall
- [ ] `history` mit ASCII-Chart
- [ ] MCP Server Integration

### Phase 3 — Nice-to-have
- [ ] launchd Service fuer macOS Autostart
- [ ] Remote Notifications (Pushover/Ntfy) fuer Hetzner
- [ ] Telegram Bot als Alternative
- [ ] Price-Drop Trend-Erkennung
