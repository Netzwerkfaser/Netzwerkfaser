# Netzwerkfaser – Kurzvideos

Automatische Erstellung von Reels, TikToks und YouTube Shorts im Netzwerkfaser-Stil.

## Format

- 1080 × 1920 (9:16), 30 fps, MP4 (H.264), ohne Ton
- Musik wird beim Hochladen in der App (Instagram/TikTok) hinzugefügt
- Farben: Jet Black `#0A0A0A`, Cerulean Blue `#007BA7`, Neon Rose `#FF2D95`
- Schrift: Inter / Inter Display
- Deutsche Untertitel unten im schwarzen Kasten ersetzen den Sprecher

## Aufruf

```bash
# Video rendern
python3 video/render.py video/beispiele/router-standort.json ausgabe.mp4

# Nur Vorschaubilder (ein JPG pro Szene) zur Kontrolle
python3 video/render.py video/beispiele/router-standort.json ausgabe.mp4 --vorschau
```

## Aufbau der JSON-Datei

```json
{
  "thema": "Router-Standort: 4 Regeln",
  "szenen": [
    {"typ": "titel", "dauer": 5.0, "label": "ROUTER-STANDORT",
     "titel": "Langsames\nWLAN?", "zusatz": "4 Regeln für den\nRouter-Standort",
     "untertitel": "Oft liegt es nicht am Internet ..."}
  ]
}
```

| Typ | Zusätzliche Felder | Zweck |
|---|---|---|
| `titel` | `zusatz` | Einstieg (Hook), großer Titel |
| `liste` | `punkte` (max. 5), `symbol` (`x` oder `haken`) | Tipps, Fehler, Checkliste |
| `balken` | `balken` (max. 4: `text`, `wert` 0–1, `farbe` blau/rosa/gold), `fussnote` | Vergleich |
| `mitte` | `vorher`, `nachher`, `geraet` | Gerät wandert in die Raummitte |
| `verbindung` | `links`, `rechts`, `kabel`, `geraet_links`, `geraet_rechts` | Zwei Geräte per Kabel verbunden |

Gerätesymbole (`geraet`, `geraet_links`, `geraet_rechts`): `router`, `kamera`, `switch`, `ap` (Access Point).
Beispiel Kamera am Switch: `"geraet_links": "switch", "geraet_rechts": "kamera", "kabel": "PoE-Kabel"`.
| `outro` | `zusatz` (optional) | Abschluss mit netzwerkfaser.de |

Gemeinsame Felder: `dauer` (Sekunden), `label` (Kapitel oben links), `titel`, `untertitel`.

Richtwert: 5–7 Szenen, insgesamt 35–45 Sekunden. Erste Szene `titel`, letzte `outro`.
Balkenwerte ohne Messung immer mit `"fussnote": "Schematische Darstellung"` kennzeichnen.

## Ablage

- `video/beispiele/` – Vorlagen
- `video/ausgabe/` – fertige Videos (Dateiname `JJJJ-MM-TT_thema.mp4`) mit der passenden JSON-Datei
