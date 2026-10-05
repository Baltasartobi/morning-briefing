"""
Morning Briefing – lokale Version.

Zeigt die Seite aus dem Ordner docs/ unter http://localhost:<port> an und
liefert unter /api/briefing frische Daten (siehe daten.py).
Gestartet wird es über start.bat. Fenster schliessen = App beenden.
"""

import json
import mimetypes
import socket
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import daten

WEB = daten.ORDNER / "docs"
CACHE_SEKUNDEN = 60     # so lange werden Daten wiederverwendet, ausser bei «Aktualisieren»

mimetypes.add_type("application/manifest+json", ".webmanifest")
mimetypes.add_type("text/javascript", ".js")

_cache = {"zeit": 0.0, "daten": None}
_cache_sperre = threading.Lock()


def briefing(neu_laden=False):
    with _cache_sperre:
        if neu_laden or not _cache["daten"] or time.time() - _cache["zeit"] > CACHE_SEKUNDEN:
            _cache["daten"] = daten.briefing_erstellen()
            _cache["zeit"] = time.time()
        return _cache["daten"]


class Anfragen(BaseHTTPRequestHandler):
    def do_GET(self):
        pfad = self.path.split("?")[0]
        if pfad == "/api/briefing":
            try:
                inhalt = json.dumps(briefing(neu_laden="neu=1" in self.path), ensure_ascii=False)
                self.senden(200, inhalt.encode("utf-8"), "application/json; charset=utf-8")
            except Exception as fehler:
                self.senden(500, json.dumps({"fehler": str(fehler)}).encode("utf-8"),
                            "application/json; charset=utf-8")
            return

        datei = (WEB / pfad.lstrip("/")).resolve()
        if pfad.endswith("/"):
            datei = datei / "index.html"
        if WEB.resolve() not in datei.parents or not datei.is_file():
            self.senden(404, b"Nicht gefunden", "text/plain")
            return
        typ = mimetypes.guess_type(datei.name)[0] or "application/octet-stream"
        if typ.startswith("text/") or typ.endswith("json") or typ.endswith("javascript"):
            typ += "; charset=utf-8"
        self.senden(200, datei.read_bytes(), typ)

    def senden(self, status, inhalt, typ):
        self.send_response(status)
        self.send_header("Content-Type", typ)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(inhalt)

    def log_message(self, *args):
        pass  # keine technischen Meldungen im Fenster


def port_belegt(port):
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def main():
    try:
        port = daten.einstellungen_laden().get("app", {}).get("port", 8765)
    except Exception as fehler:
        print("Fehler in einstellungen.toml:", fehler)
        print("Bitte die Datei prüfen (Anführungszeichen, [[...]]-Zeilen).")
        sys.exit(1)

    adresse = f"http://localhost:{port}"
    if port_belegt(port):
        print("Die App läuft bereits – öffne den Browser.")
        webbrowser.open(adresse)
        return

    server = ThreadingHTTPServer(("127.0.0.1", port), Anfragen)
    print("=" * 56)
    print("  Morning Briefing läuft auf", adresse)
    print("  Dieses Fenster offen lassen. Schliessen = App beenden.")
    print("=" * 56)
    if "--ohne-browser" not in sys.argv:
        threading.Timer(0.8, lambda: webbrowser.open(adresse)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
