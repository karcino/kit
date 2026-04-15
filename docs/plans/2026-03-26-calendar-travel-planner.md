# Kit Feature: Calendar Travel Planner

> Status: Konzept | Erstellt: 26.03.2026
> Prioritaet: Mittel — manuell funktioniert, Automatisierung spart Zeit + verhindert Fehler

## Problem

Kalender-Events haben Orte, aber keine Anfahrt-Planung. Fuer jeden Termin
muss manuell die Route nachgeschaut und ein Wecker gestellt werden.
Fehlerquellen: falsche Abfahrtszeiten, verpasste Verbindungen, kein Backup.

Betrifft alle Kalender — Arbeit, Arzt, Meetings, Uni, Events.

## Loesung

Neues Kit-Tool: `kit travel` / `kit_travel`

Scannt Calendar-Events, berechnet Anfahrten per OEPNV/Fuss/Rad,
erstellt Travel-Events mit Primaer- + Backup-Verbindung im DB-Navigator-Format.

## Architektur

```
Calendar Source (Apple Calendar / Google Calendar)
      │
      ▼
kit travel sync [--calendar "Name"] [--days 7] [--dry-run]
      │
      ├── Events mit Location lesen
      │   ├── Location-Feld direkt nutzen
      │   └── ODER Alias-Lookup (Kurzname → Adresse)
      │
      ├── Events ohne Location skippen
      │
      ├── Events die schon ein "Anfahrt"-Event haben skippen
      │
      └── Pro Event:
          ├── kit_route(home → location, arrive = start - buffer)    → Primaer
          ├── kit_route(home → location, arrive = start - buffer*2)  → Backup
          │
          └── Travel-Event erstellen
              ├── Kalender: gleicher wie Original-Event
              ├── Titel: "Anfahrt {Eventname|Ort}"
              ├── Start: Abfahrtszeit Primaer-Verbindung
              ├── Ende: Ankunft (= Event-Start - buffer)
              ├── Location: Zieladresse
              ├── Notes: DB-Navigator-Format
              └── Alarm: 5 Min vorher
```

## CLI Interface

```bash
# Vorschau: was wuerde erstellt werden?
kit travel sync --dry-run

# Sync fuer alle Kalender, naechste 7 Tage
kit travel sync --days 7

# Nur bestimmter Kalender
kit travel sync --calendar "AD Berlin" --days 14

# Einzelnen Termin
kit travel plan "Arzt morgen 09:00" --to "Gruenberger Str. 43, Berlin"

# Buffer konfigurieren (Default: 10 Min)
kit travel sync --buffer 15
```

## MCP Tools

```
kit_travel_sync(calendar?, days?, buffer_minutes?, dry_run?)
  → Scannt + erstellt Travel-Events

kit_travel_plan(event_title, destination, arrive_by, buffer_minutes?)
  → Einzelne Anfahrt planen + eintragen
```

## Location Aliases

Kurzname-zu-Adresse-Mapping in Config fuer Events ohne vollstaendige Adresse:

```toml
[location_aliases]
EnDe = "Hermannstr. 127, 12051 Berlin"
UdK = "Hardenbergstr. 33, 10623 Berlin"
HU = "Unter den Linden 6, 10099 Berlin"
home = "Danneckerstr. 14, 10245 Berlin"  # already in [general]
```

Resolution-Reihenfolge:
1. Event Location-Feld (wenn vollstaendige Adresse)
2. Alias-Lookup (wenn Kurzname im Titel oder Location)
3. Skip (wenn nichts gefunden)

## Notes-Format (DB-Navigator-Stil)

```
Anfahrt {Termin} — {Adresse}

VERBINDUNG 1 (Ankunft {HH:MM}, {N} Min vor Termin)
ab {HH:MM}  {Start} (losgehen)
ab {HH:MM}  {Station} — {Linie} ({N} Stops)
[ab {HH:MM}  {Umstieg} — {Linie} ({N} Stops)]
an {HH:MM}  {Zielstation}
ab {HH:MM}  Fussweg ({N} Min)
an {HH:MM}  {Zieladresse}

{N} Min, {N}x umsteigen
Gleise + Echtzeit: {DB Navigator Link}
BVG: {BVG Link}
Maps: {Google Maps Link}

---
VERBINDUNG 2 / BACKUP (Ankunft {HH:MM}, {N} Min vor Termin)
[gleiche Struktur]
```

## Duplikat-Erkennung

Verhindert doppelte Anfahrt-Events bei mehrfachem Ausfuehren:

1. Travel-Events bekommen Prefix "Anfahrt " im Titel
2. Vor Insert: Check ob Event mit "Anfahrt" + aehnlicher Startzeit existiert
3. `--force` Flag zum Ueberschreiben bestehender Travel-Events

## Calendar Access

| Quelle | Methode | Status |
|--------|---------|--------|
| Google Calendar | `kit.cal.google_cal` (bereits implementiert) | Ready |
| Apple Calendar | osascript via subprocess | Machbar, fragil |
| Apple Calendar | EventKit via PyObjC | Robust, mehr Aufwand |

Empfehlung: Google Calendar als primaere Quelle (bereits in Kit),
Apple Calendar als Read-Only via osascript fuer Sync.

## Offene Punkte

1. **Gleis-Nummern**: Google Maps API hat keine Bahnsteig-Daten.
   Spaeter: BVG HAFAS API (hafas-client) integrieren.

2. **Rueckfahrt**: Aktuell nur Hinfahrt. Rueckfahrt-Events optional?

3. **Modus-Wahl**: Transit als Default, aber bei kurzen Strecken
   automatisch Walking vorschlagen? Oder per Config?

4. **Ganztaegige Events**: Skippen (kein sinnvoller Anfahrtszeitpunkt).

## Implementation Steps

1. [ ] `[location_aliases]` Config-Section
2. [ ] Calendar Reader Abstraction (Google Cal + Apple Cal osascript)
3. [ ] Duplikat-Erkennung
4. [ ] `kit travel sync` CLI Command
5. [ ] `kit travel plan` CLI Command
6. [ ] `kit_travel_sync` + `kit_travel_plan` MCP Tools
7. [ ] Dry-Run-Modus
8. [ ] Dark Factory Scheduled Task
9. [ ] BVG HAFAS fuer Gleis-Nummern (spaeter)

## Dark Factory Task

```
name: travel-planner-sync
schedule: "0 3 * * *"  # 03:00 nachts
prompt: |
  Fuehre `kit travel sync --days 7` aus.
  Fuer jeden Kalender-Event mit Location aber ohne Anfahrt-Event:
  1. Adresse aus Location-Feld oder Alias-Tabelle
  2. Primaer-Route (Ankunft 10 Min vor Termin)
  3. Backup-Route (Ankunft 15 Min vor Termin)
  4. Anfahrt-Event im DB-Navigator-Format erstellen
  Report: Anzahl erstellte Events, uebersprungene Events, Fehler.
```
