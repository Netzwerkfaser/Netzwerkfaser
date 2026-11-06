#!/usr/bin/env python3
"""
Netzwerkfaser – Kurzvideo-Renderer (Reels, TikTok, Shorts)

Erstellt ein Hochformat-Video (1080x1920, 30 fps, ohne Ton) im Netzwerkfaser-Stil
aus einer JSON-Szenendatei.

Aufruf:
    python3 video/render.py video/beispiele/router-standort.json ausgabe.mp4

Benötigt: Python 3, Pillow, ffmpeg, Schrift Inter (/usr/share/fonts/opentype/inter/).

Szenentypen (Feld "typ"):
    titel       – großer Titel, Untertitel in Blau, blinkende Signalbalken
    liste       – Überschrift + bis zu 5 Punkte mit Symbol ("x" oder "haken")
    balken      – Überschrift + Balkenvergleich (Werte 0.0–1.0), optionale Fußnote
    mitte       – Überschrift + Grundriss, Gerät wandert von der Ecke in die Mitte
    verbindung  – Überschrift + zwei Geräte, per Kabel verbunden
    outro       – Logo, Leistungen, Button mit Website

Gemeinsame Felder jeder Szene:
    dauer      Sekunden (z. B. 7.0)
    label      Kapitel-Label oben links (Großbuchstaben, z. B. "01 · ZENTRAL")
    titel      Überschrift (Zeilenumbruch mit \n)
    untertitel Text im schwarzen Kasten unten (ersetzt den Sprecher)
"""
import json
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
BG = (10, 10, 10)          # Jet Black #0A0A0A
BLUE = (0, 123, 167)       # Cerulean Blue #007BA7
ROSE = (255, 45, 149)      # Neon Rose #FF2D95
WHITE = (245, 245, 245)
GREY = (120, 120, 130)
DARK = (28, 28, 34)
GOLD = (200, 160, 60)
FONT_DIR = "/usr/share/fonts/opentype/inter/"

_fonts = {}


def F(name, size):
    key = (name, size)
    if key not in _fonts:
        try:
            _fonts[key] = ImageFont.truetype(FONT_DIR + name + ".otf", size)
        except OSError:
            _fonts[key] = ImageFont.load_default(size)
    return _fonts[key]


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def mix(c1, c2, a):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * a) for i in range(3))


def farbe(name):
    return {"blau": BLUE, "rosa": ROSE, "gold": GOLD, "weiss": WHITE, "grau": GREY}.get(name, BLUE)


def wrap(text, font, maxw, d):
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if d.textlength(t, font=font) <= maxw:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    return lines


# ---------------- Grundelemente ----------------

def basis(label):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    for x in range(0, W, 90):
        d.line([(x, 0), (x, H)], fill=(18, 18, 22))
    for y in range(0, H, 90):
        d.line([(0, y), (W, y)], fill=(18, 18, 22))
    d.text((60, 90), label, font=F("Inter-Bold", 34), fill=ROSE, anchor="lm")
    d.text((W - 60, 90), "NETZWERKFASER", font=F("Inter-Bold", 34), fill=BLUE, anchor="rm")
    d.rectangle([60, 130, W - 60, 134], fill=DARK)
    return im, d


def untertitel(d, text, t):
    if not text:
        return
    a = ease(t / 0.35)
    font = F("Inter-SemiBold", 46)
    lines = wrap(text, font, W - 200, d)
    lh = 62
    bh = lh * len(lines) + 50
    y0 = H - 330 - bh // 2
    d.rounded_rectangle([70, y0, W - 70, y0 + bh], radius=22, fill=(0, 0, 0),
                        outline=(40, 40, 48), width=2)
    for i, ln in enumerate(lines):
        d.text((W // 2, y0 + 25 + lh * i + lh // 2), ln, font=font,
               fill=mix(BG, WHITE, a), anchor="mm")


def ueberschrift(d, text, t, y=330, size=96, color=WHITE, delay=0.0):
    if not text:
        return
    a = ease((t - delay) / 0.5)
    dy = int((1 - a) * 40)
    font = F("InterDisplay-Black", size)
    zeilen = text.split("\n")
    # zu lange Zeilen automatisch verkleinern
    while size > 48 and max(d.textlength(z, font=font) for z in zeilen) > W - 120:
        size -= 6
        font = F("InterDisplay-Black", size)
    for i, ln in enumerate(zeilen):
        d.text((W // 2, y + dy + i * int(size * 1.12)), ln, font=font,
               fill=mix(BG, color, a), anchor="mm")


def ringe(d, cx, cy, t, n=4, maxr=380, color=BLUE, speed=0.6, staerke=1.0):
    for i in range(n):
        p = ((t * speed) + i / n) % 1.0
        r = 40 + p * maxr
        col = mix(BG, color, (1 - p) * staerke)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col, width=6)


def router(d, cx, cy, s=1.0, col=WHITE):
    w, h = int(170 * s), int(70 * s)
    d.rounded_rectangle([cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2],
                        radius=int(14 * s), fill=DARK, outline=col, width=4)
    for k in (-1, 1):
        x = cx + k * int(55 * s)
        d.line([(x, cy - h // 2), (x + k * int(12 * s), cy - h // 2 - int(60 * s))],
               fill=col, width=int(7 * s))
    for k in range(3):
        x = cx - int(40 * s) + k * int(40 * s)
        d.ellipse([x - 6, cy - 6, x + 6, cy + 6], fill=BLUE if k < 2 else ROSE)


def geraet_rund(d, cx, cy, s=1.0):
    r = int(60 * s)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=DARK, outline=WHITE, width=4)
    d.ellipse([cx - 12, cy - 12, cx + 12, cy + 12], fill=BLUE)


def kamera(d, cx, cy, s=1.0, col=WHITE):
    w, h = int(170 * s), int(80 * s)
    # Halterung
    d.line([(cx - w // 2 + 20, cy), (cx - w // 2 - 30, cy + int(70 * s))], fill=col, width=int(8 * s))
    d.rectangle([cx - w // 2 - 60, cy + int(70 * s), cx - w // 2, cy + int(84 * s)], fill=col)
    # Gehäuse und Objektiv
    d.rounded_rectangle([cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2],
                        radius=int(18 * s), fill=DARK, outline=col, width=4)
    lx = cx + w // 2 - int(10 * s)
    lr = int(30 * s)
    d.ellipse([lx - lr, cy - lr, lx + lr, cy + lr], fill=DARK, outline=col, width=4)
    d.ellipse([lx - lr // 2, cy - lr // 2, lx + lr // 2, cy + lr // 2], fill=BLUE)
    d.ellipse([cx - w // 2 + 18, cy - 8, cx - w // 2 + 34, cy + 8], fill=ROSE)


def switch(d, cx, cy, s=1.0, col=WHITE):
    w, h = int(220 * s), int(60 * s)
    d.rounded_rectangle([cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2],
                        radius=int(10 * s), fill=DARK, outline=col, width=4)
    for k in range(6):
        x = cx - w // 2 + int(24 * s) + k * int(30 * s)
        d.rectangle([x, cy - int(10 * s), x + int(20 * s), cy + int(12 * s)],
                    outline=BLUE if k % 2 == 0 else ROSE, width=3)


def geraet(d, art, cx, cy, s=1.0):
    """Zeichnet ein Gerätesymbol: router, kamera, switch, ap."""
    if art == "kamera":
        kamera(d, cx, cy, s)
    elif art == "switch":
        switch(d, cx, cy, s)
    elif art == "ap":
        geraet_rund(d, cx, cy, s)
    else:
        router(d, cx, cy, s)


# ---------------- Szenentypen ----------------

def sz_titel(s, t, dur):
    im, d = basis(s.get("label", ""))
    ueberschrift(d, s.get("titel", ""), t, y=420, size=140)
    ueberschrift(d, s.get("zusatz", ""), t, y=760, size=64, color=BLUE, delay=0.8)
    cx, cy = W // 2, 1150
    lvl = 1 if int(t * 3) % 2 == 0 else 2
    for i in range(4):
        bh = 50 + i * 45
        x = cx - 150 + i * 90
        d.rounded_rectangle([x, cy + 100 - bh, x + 60, cy + 100], radius=10,
                            fill=ROSE if i < lvl else DARK)
    untertitel(d, s.get("untertitel", ""), t)
    return im


def sz_liste(s, t, dur):
    im, d = basis(s.get("label", ""))
    ueberschrift(d, s.get("titel", ""), t)
    symbol = s.get("symbol", "x")
    punkte = s.get("punkte", [])[:5]
    for i, text in enumerate(punkte):
        y = 700 + i * 170
        p = ease((t - 0.7 - i * 0.55) / 0.5)
        if p <= 0:
            continue
        x = 140 - int((1 - p) * 60)
        d.rounded_rectangle([x, y - 60, W - 140, y + 60], radius=20, fill=mix(BG, DARK, p))
        cx = x + 70
        if symbol == "haken":
            col = mix(BG, BLUE, p)
            d.ellipse([cx - 34, y - 34, cx + 34, y + 34], outline=col, width=6)
            d.line([(cx - 16, y + 2), (cx - 4, y + 15), (cx + 18, y - 14)], fill=col, width=7)
        else:
            col = mix(BG, ROSE, p)
            d.ellipse([cx - 34, y - 34, cx + 34, y + 34], outline=col, width=6)
            d.line([(cx - 16, y - 16), (cx + 16, y + 16)], fill=col, width=7)
            d.line([(cx - 16, y + 16), (cx + 16, y - 16)], fill=col, width=7)
        font = F("Inter-SemiBold", 54)
        while font.size > 34 and d.textlength(text, font=font) > W - 140 - (x + 160):
            font = F("Inter-SemiBold", font.size - 4)
        d.text((x + 140, y), text, font=font, fill=mix(BG, WHITE, p), anchor="lm")
    untertitel(d, s.get("untertitel", ""), t)
    return im


def sz_balken(s, t, dur):
    im, d = basis(s.get("label", ""))
    ueberschrift(d, s.get("titel", ""), t)
    for i, b in enumerate(s.get("balken", [])[:4]):
        y = 720 + i * 210
        p = ease((t - 0.8 - i * 0.5) / 0.9)
        d.text((120, y), b.get("text", ""), font=F("Inter-SemiBold", 50), fill=WHITE, anchor="lm")
        d.rounded_rectangle([120, y + 45, W - 120, y + 105], radius=16, fill=DARK)
        wbar = int((W - 240) * clamp(float(b.get("wert", 0.5))) * p)
        if wbar > 20:
            d.rounded_rectangle([120, y + 45, 120 + wbar, y + 105], radius=16,
                                fill=farbe(b.get("farbe", "blau")))
    if s.get("fussnote"):
        d.text((W // 2, 1380), s["fussnote"], font=F("Inter-Regular", 34), fill=GREY, anchor="mm")
    untertitel(d, s.get("untertitel", ""), t)
    return im


def sz_mitte(s, t, dur):
    im, d = basis(s.get("label", ""))
    ueberschrift(d, s.get("titel", ""), t)
    x0, y0, x1, y1 = 120, 620, W - 120, 1330
    d.rectangle([x0, y0, x1, y1], outline=GREY, width=6)
    d.line([(W // 2, y0), (W // 2, y0 + 250)], fill=GREY, width=6)
    d.line([(x0, 1000), (x0 + 260, 1000)], fill=GREY, width=6)
    d.line([(x1 - 260, 1000), (x1, 1000)], fill=GREY, width=6)
    p = ease((t - 1.2) / 1.6)
    sx, sy = x0 + 110, y1 - 80
    ex, ey = W // 2, 975
    cx, cy = int(sx + (ex - sx) * p), int(sy + (ey - sy) * p)
    ringe(d, cx, cy, t, maxr=430, color=BLUE if p > 0.9 else ROSE, staerke=0.9)
    geraet(d, s.get("geraet", "router"), cx, cy, 0.9)
    tag = s.get("vorher", "Ecke: schwach") if p < 0.5 else s.get("nachher", "Mitte: gut verteilt")
    d.text((W // 2, y1 + 70), tag, font=F("Inter-Bold", 48), fill=ROSE if p < 0.5 else BLUE, anchor="mm")
    untertitel(d, s.get("untertitel", ""), t)
    return im


def sz_verbindung(s, t, dur):
    im, d = basis(s.get("label", ""))
    ueberschrift(d, s.get("titel", ""), t, size=92)
    ax, bx, yy = 270, W - 270, 1000
    p = ease((t - 1.0) / 1.2)
    ringe(d, ax, yy, t, maxr=260, staerke=0.7)
    if p > 0.6:
        ringe(d, bx, yy, t + 0.3, maxr=260, staerke=0.7 * ease((p - 0.6) / 0.4))
    d.line([(ax, yy + 60), (ax, yy + 180), (ax + int((bx - ax) * p), yy + 180)], fill=ROSE, width=8)
    if p > 0.98:
        d.line([(bx, yy + 180), (bx, yy + 60)], fill=ROSE, width=8)
    geraet(d, s.get("geraet_links", "router"), ax, yy, 0.8)
    if p > 0.6:
        geraet(d, s.get("geraet_rechts", "ap"), bx, yy, 0.8)
    d.text((ax, yy + 300), s.get("links", "Router"), font=F("Inter-Bold", 44), fill=WHITE, anchor="mm")
    d.text((bx, yy + 300), s.get("rechts", "Access Point"), font=F("Inter-Bold", 44), fill=WHITE, anchor="mm")
    d.text((W // 2, yy + 240), s.get("kabel", "LAN-Kabel"), font=F("Inter-SemiBold", 38), fill=ROSE, anchor="mm")
    untertitel(d, s.get("untertitel", ""), t)
    return im


def sz_outro(s, t, dur):
    im, d = basis(s.get("label", "KONTAKT"))
    ringe(d, W // 2, 820, t, n=5, maxr=520, staerke=0.5)
    ueberschrift(d, "NETZWERKFASER", t, y=780, size=104)
    ueberschrift(d, s.get("zusatz", "Netzwerk · Glasfaser · Kameras\nSmart Home in Köln"),
                 t, y=920, size=50, color=BLUE, delay=0.4)
    a = ease((t - 1.0) / 0.5)
    d.rounded_rectangle([200, 1120, W - 200, 1240], radius=60, fill=mix(BG, ROSE, a))
    d.text((W // 2, 1180), "netzwerkfaser.de", font=F("Inter-Bold", 56), fill=mix(BG, WHITE, a), anchor="mm")
    untertitel(d, s.get("untertitel", "Termin unter netzwerkfaser.de."), t)
    return im


TYPEN = {
    "titel": sz_titel,
    "liste": sz_liste,
    "balken": sz_balken,
    "mitte": sz_mitte,
    "verbindung": sz_verbindung,
    "outro": sz_outro,
}


# ---------------- Rendern ----------------

def bild(szene, t, dur, t_global, gesamt):
    im = TYPEN[szene["typ"]](szene, t, dur)
    d = ImageDraw.Draw(im)
    d.rectangle([60, 130, 60 + int((W - 120) * t_global / gesamt), 134], fill=ROSE)
    fade = min(clamp(t / 0.25), clamp((dur - t) / 0.25))
    if fade < 1:
        im = Image.blend(Image.new("RGB", (W, H), BG), im, fade)
    return im


def szene_rendern(szene, dur, offset, gesamt, ziel):
    tmp = ziel[:-4] + ".part.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
           "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS), tmp]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(int(round(dur * FPS))):
        t = i / FPS
        proc.stdin.write(bild(szene, t, dur, offset + t, gesamt).tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit("ffmpeg-Fehler in Szene: " + szene.get("label", szene["typ"]))
    os.replace(tmp, ziel)


def vorschau(szenen, ausgabe):
    """Speichert je Szene ein JPG (bei 70 % der Szenendauer) zur Kontrolle."""
    gesamt = sum(float(s["dauer"]) for s in szenen)
    off = 0.0
    pfade = []
    for i, s in enumerate(szenen):
        dur = float(s["dauer"])
        p = f"{ausgabe[:-4]}_vorschau_{i + 1:02d}.jpg"
        bild(s, dur * 0.7, dur, off + dur * 0.7, gesamt).save(p, quality=85)
        pfade.append(p)
        off += dur
    return pfade


def main():
    if len(sys.argv) < 3:
        sys.exit("Aufruf: python3 render.py szenen.json ausgabe.mp4 [--vorschau]")
    with open(sys.argv[1], encoding="utf-8") as f:
        daten = json.load(f)
    szenen = daten["szenen"]
    for s in szenen:
        if s.get("typ") not in TYPEN:
            sys.exit(f"Unbekannter Szenentyp: {s.get('typ')} (erlaubt: {', '.join(TYPEN)})")
    ausgabe = os.path.abspath(sys.argv[2])
    if "--vorschau" in sys.argv:
        for p in vorschau(szenen, ausgabe):
            print(p)
        return
    gesamt = sum(float(s["dauer"]) for s in szenen)
    with tempfile.TemporaryDirectory() as tmp:
        teile, off = [], 0.0
        for i, s in enumerate(szenen):
            dur = float(s["dauer"])
            ziel = os.path.join(tmp, f"szene_{i:02d}.mp4")
            szene_rendern(s, dur, off, gesamt, ziel)
            teile.append(ziel)
            off += dur
        liste = os.path.join(tmp, "liste.txt")
        with open(liste, "w") as f:
            for p in teile:
                f.write(f"file '{p}'\n")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                        "-i", liste, "-c", "copy", ausgabe], check=True)
    print(f"Fertig: {ausgabe} ({gesamt:.1f} s)")


if __name__ == "__main__":
    main()
