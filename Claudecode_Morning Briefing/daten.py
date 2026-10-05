"""
Morning Briefing – Daten holen.

Sammelt Kurse, Zinsen und Schlagzeilen gemäss einstellungen.toml.
Wird von app.py (lokale Version) und von GitHub Actions (Handy-Version) genutzt.

Direkt aufrufen:   python daten.py docs/data.json [--oeffentlich]
--oeffentlich lässt die Artikel-Anrisse weg (für die öffentliche GitHub-Seite).
"""

import csv
import html
import io
import json
import re
import sys
import tomllib
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from curl_cffi import requests

ORDNER = Path(__file__).resolve().parent
EINSTELLUNGEN = ORDNER / "einstellungen.toml"

ZEITLIMIT_GESAMT = 30   # Sekunden, danach gilt eine Quelle als «nicht verfügbar»
ZEITLIMIT_ANFRAGE = 12  # Sekunden pro einzelne Anfrage
VERLAUF_TAGE = 5        # Punkte im Mini-Verlauf (Sparkline)


def einstellungen_laden():
    with open(EINSTELLUNGEN, "rb") as f:
        return tomllib.load(f)


def holen(url, **kwargs):
    antwort = requests.get(url, timeout=ZEITLIMIT_ANFRAGE,
                           headers={"User-Agent": "Mozilla/5.0 MorningBriefing", **kwargs.pop("headers", {})},
                           **kwargs)
    antwort.raise_for_status()
    return antwort


# ---------------------------------------------------------------- Kurse (Yahoo Finance)

def kurse_holen(eintraege):
    """Kurs, Vortageskurs, Veränderung in % und 5-Tage-Verlauf pro Eintrag."""
    import yfinance as yf

    ergebnis = {}
    symbole = sorted({e["symbol"] for e in eintraege})
    if not symbole:
        return ergebnis
    daten = yf.download(symbole, period="15d", interval="1d", progress=False,
                        group_by="ticker", threads=True, auto_adjust=False)
    heute = datetime.now().date()
    for symbol in symbole:
        try:
            schluss = daten[symbol]["Close"].dropna()
            if len(schluss) < 2:
                continue
            kurs, vortag = float(schluss.iloc[-1]), float(schluss.iloc[-2])
            datum = schluss.index[-1].date()
            ergebnis[symbol] = {
                "kurs": kurs,
                "vortag": vortag,
                "veraenderung_pct": (kurs / vortag - 1) * 100,
                "datum": datum.isoformat(),
                "ist_heute": datum == heute,
                "verlauf": [round(float(x), 6) for x in schluss.iloc[-VERLAUF_TAGE:]],
            }
        except Exception:
            pass
    return ergebnis


def kurszeilen(eintraege, kurse):
    zeilen = []
    for e in eintraege:
        zeile = {"name": e["name"], "symbol": e["symbol"], "einheit": e.get("einheit", ""),
                 "dezimalen": e.get("dezimalen", 2), "verfuegbar": e["symbol"] in kurse}
        zeile.update(kurse.get(e["symbol"], {}))
        zeilen.append(zeile)
    return zeilen


# ---------------------------------------------------------------- Zinsen

def zins_snb():
    """Rendite 10-jährige Bundesanleihen der Eidgenossenschaft (SNB-Datenportal, Tageswerte)."""
    von = (date.today() - timedelta(days=25)).isoformat()
    text = holen(f"https://data.snb.ch/api/warehouse/cube/SNB1A.SNB.NSS.KZS.EID/data/csv/de?fromDate={von}").text
    werte = []
    for zeile in csv.reader(io.StringIO(text), delimiter=";"):
        if len(zeile) >= 6 and zeile[1] == "J10M0" and zeile[5]:
            werte.append((zeile[0], float(zeile[5])))
    return sorted(werte)


def zins_bundesbank():
    """Rendite 10-jährige Bundeswertpapiere (Bundesbank, Tageswerte)."""
    von = (date.today() - timedelta(days=25)).isoformat()
    url = ("https://api.statistiken.bundesbank.de/rest/data/BBSIS/"
           f"D.I.ZST.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A?startPeriod={von}")
    text = holen(url, headers={"Accept": "application/vnd.sdmx.data+csv;version=1.0.0"}).text.lstrip("﻿")
    zeilen = list(csv.reader(io.StringIO(text), delimiter=";"))
    kopf = zeilen[0]
    i_datum, i_wert = kopf.index("TIME_PERIOD"), kopf.index("OBS_VALUE")
    werte = []
    for z in zeilen[1:]:
        try:
            werte.append((z[i_datum], float(z[i_wert].replace(",", "."))))
        except (IndexError, ValueError):
            pass  # Feiertage sind mit «.» markiert
    return sorted(werte)


def zinszeile(eintrag, werte):
    zeile = {"name": eintrag["name"], "quelle": eintrag["quelle"], "verfuegbar": False}
    if len(werte) >= 2:
        (datum, wert), (_, vortag) = werte[-1], werte[-2]
        zeile.update({
            "verfuegbar": True,
            "wert": wert,
            "vortag": vortag,
            "veraenderung_bp": round((wert - vortag) * 100, 1),
            "datum": datum,
            "ist_heute": datum == date.today().isoformat(),
            "verlauf": [w for _, w in werte[-VERLAUF_TAGE:]],
        })
    return zeile


# ---------------------------------------------------------------- News (RSS)

def text_bereinigen(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def feed_holen(quelle, anzahl):
    import feedparser

    feed = feedparser.parse(holen(quelle["url"]).content)
    artikel = []
    for eintrag in feed.entries:
        zeit = eintrag.get("published_parsed") or eintrag.get("updated_parsed")
        artikel.append({
            "titel": text_bereinigen(eintrag.get("title")),
            "link": eintrag.get("link", ""),
            "anriss": text_bereinigen(eintrag.get("summary"))[:600],
            "zeit": datetime(*zeit[:6], tzinfo=timezone.utc).isoformat() if zeit else None,
            "quelle": quelle["name"],
            "gruppe": quelle.get("gruppe", ""),
            "sprache": quelle.get("sprache", "de"),
        })
    artikel.sort(key=lambda a: a["zeit"] or "", reverse=True)
    return artikel[:anzahl]


# ---------------------------------------------------------------- «Heute in 30 Sekunden»

def zahl(wert, dezimalen=2):
    return f"{wert:,.{dezimalen}f}".replace(",", "'")


def pct(wert):
    return ("+" if wert > 0 else "−" if wert < 0 else "±") + f"{abs(wert):.2f}%"


def kernaussagen(maerkte, devisen):
    """Drei regelbasierte Kernaussagen, ganz ohne KI."""
    aussagen = []
    ok = [m for m in maerkte if m["verfuegbar"]]

    # 1) Aktienmärkte: SMI plus der stärkste bzw. schwächste Markt
    smi = next((m for m in ok if m["symbol"] == "^SSMI"), None)
    andere = [m for m in ok if m is not smi]
    if andere:
        bester = max(andere, key=lambda m: m["veraenderung_pct"])
        schwaechster = min(andere, key=lambda m: m["veraenderung_pct"])
        markt, wort = (bester, "führt") if bester["veraenderung_pct"] >= -schwaechster["veraenderung_pct"] \
            else (schwaechster, "am schwächsten")
        start = f"SMI {pct(smi['veraenderung_pct'])}, " if smi else ""
        aussagen.append(f"{start}{markt['name']} {pct(markt['veraenderung_pct'])} {wort}")
    elif smi:
        aussagen.append(f"SMI {pct(smi['veraenderung_pct'])}")

    # 2) Franken gemessen an EUR/CHF
    eurchf = next((d for d in devisen if d["symbol"] == "EURCHF=X" and d["verfuegbar"]), None)
    if eurchf:
        p = eurchf["veraenderung_pct"]
        lage = "Franken stabil" if abs(p) < 0.05 else "Franken stärker" if p < 0 else "Franken schwächer"
        aussagen.append(f"{lage}: EUR/CHF {zahl(eurchf['kurs'], 4)} ({pct(p)})")

    # 3) Grösste Bewegung bei Rohstoffen/Krypto, dazu Schwellen beim Öl
    rohstoffe = [d for d in devisen if d["verfuegbar"] and "/" not in d["name"]]
    if rohstoffe:
        groesste = max(rohstoffe, key=lambda d: abs(d["veraenderung_pct"]))
        text = f"{groesste['name']} {pct(groesste['veraenderung_pct'])} auf {zahl(groesste['kurs'], groesste['dezimalen'])} {groesste['einheit']}".strip()
        brent = next((d for d in rohstoffe if d["symbol"] == "BZ=F"), None)
        if brent and brent is not groesste and (brent["kurs"] >= 100 or brent["kurs"] < 60):
            richtung = "über 100" if brent["kurs"] >= 100 else "unter 60"
            text += f" · Brent {richtung} USD"
        elif brent and brent is groesste and brent["kurs"] >= 100:
            text = f"Brent über 100 USD: {zahl(brent['kurs'])} ({pct(brent['veraenderung_pct'])})"
        aussagen.append(text)

    return aussagen[:3]


# ---------------------------------------------------------------- Alles zusammen

def briefing_erstellen(oeffentlich=False):
    cfg = einstellungen_laden()
    anzahl = cfg.get("app", {}).get("news_pro_quelle", 10)
    maerkte_cfg = cfg.get("maerkte", [])
    devisen_cfg = cfg.get("devisen_rohstoffe", [])
    watch_cfg = cfg.get("watchlist", [])
    zins_cfg = cfg.get("zinsen", [])
    quellen = cfg.get("news", [])

    yahoo = maerkte_cfg + devisen_cfg + watch_cfg + [z for z in zins_cfg if z["quelle"] == "yahoo"]
    zins_funktionen = {"snb": zins_snb, "bundesbank": zins_bundesbank}

    pool = ThreadPoolExecutor(max_workers=10)
    auftrag_kurse = pool.submit(kurse_holen, yahoo)
    auftraege_zinsen = [pool.submit(zins_funktionen[z["quelle"]]) if z["quelle"] in zins_funktionen else None
                        for z in zins_cfg]
    auftraege_news = [pool.submit(feed_holen, q, anzahl) for q in quellen]
    wait([auftrag_kurse, *[a for a in auftraege_zinsen if a], *auftraege_news], timeout=ZEITLIMIT_GESAMT)
    pool.shutdown(wait=False, cancel_futures=True)

    def ergebnis(auftrag, ersatz):
        try:
            return auftrag.result(timeout=0)
        except Exception:
            return ersatz

    kurse = ergebnis(auftrag_kurse, {})

    zinsen = []
    for eintrag, auftrag in zip(zins_cfg, auftraege_zinsen):
        if eintrag["quelle"] == "yahoo":
            k = kurse.get(eintrag["symbol"])
            werte = [(k["datum"], w) for w in k["verlauf"]] if k else []
        else:
            werte = ergebnis(auftrag, [])
        zinsen.append(zinszeile(eintrag, werte))

    artikel, quellen_status = [], []
    for quelle, auftrag in zip(quellen, auftraege_news):
        liste = ergebnis(auftrag, [])
        quellen_status.append({"name": quelle["name"], "gruppe": quelle.get("gruppe", ""), "verfuegbar": bool(liste)})
        artikel.extend(liste)
    gesehen = set()
    artikel = [a for a in sorted(artikel, key=lambda a: a["zeit"] or "", reverse=True)
               if not (a["titel"].lower() in gesehen or gesehen.add(a["titel"].lower()))]
    if oeffentlich:
        for a in artikel:
            a.pop("anriss", None)

    maerkte = kurszeilen(maerkte_cfg, kurse)
    devisen = kurszeilen(devisen_cfg, kurse)
    return {
        "aktualisiert": datetime.now().astimezone().isoformat(timespec="seconds"),
        "kernaussagen": kernaussagen(maerkte, devisen),
        "maerkte": maerkte,
        "devisen_rohstoffe": devisen,
        "zinsen": zinsen,
        "watchlist": kurszeilen(watch_cfg, kurse),
        "news": {"quellen": quellen_status, "artikel": artikel},
    }


if __name__ == "__main__":
    ziel = Path(sys.argv[1]) if len(sys.argv) > 1 else ORDNER / "docs" / "data.json"
    daten = briefing_erstellen(oeffentlich="--oeffentlich" in sys.argv)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(json.dumps(daten, ensure_ascii=False, indent=1), encoding="utf-8")
    fehlend = [z["name"] for teil in ("maerkte", "devisen_rohstoffe", "zinsen", "watchlist")
               for z in daten[teil] if not z["verfuegbar"]]
    fehlend += [q["name"] for q in daten["news"]["quellen"] if not q["verfuegbar"]]
    print(f"Gespeichert: {ziel} ({len(daten['news']['artikel'])} Artikel)")
    print("Nicht verfügbar:", ", ".join(fehlend) if fehlend else "–")
