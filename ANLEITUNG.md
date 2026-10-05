# Morning Briefing – Anleitung

Es gibt zwei Versionen, die gleich aussehen:

| | Lokale Version (Laptop) | Handy-Version (GitHub) |
|---|---|---|
| Start | Doppelklick auf `start.bat` | App-Symbol auf dem Home-Bildschirm |
| Daten | bei jedem Klick auf ⟳ ganz frisch | werktags 06–22 Uhr alle 30 Min. erneuert |
| Laptop muss laufen | ja | nein |
| Öffentlich sichtbar | nein | ja (wer die Adresse kennt) |

---

## 1. Lokale Version starten
1. Im Ordner doppelt auf **`start.bat`** klicken.
2. Ein schwarzes Fenster öffnet sich – **offen lassen**. Der Browser öffnet sich automatisch.
   Falls nicht: im Browser **http://localhost:8765** eingeben.
3. **⟳** oben rechts holt neue Daten, **☀/☾** wechselt zwischen hell und dunkel.
4. **Beenden:** das schwarze Fenster schliessen.

Tipp: Rechtsklick auf `start.bat` → *Senden an* → *Desktop (Verknüpfung erstellen)*.

---

## 2. Watchlist, Märkte, Devisen oder News ändern
Alles steht in **`einstellungen.toml`** (Rechtsklick → *Öffnen mit* → *Editor*).

```toml
[[watchlist]]
name = "Nestlé"
symbol = "NESN.SW"
einheit = "CHF"
```

- **name**: frei wählbar
- **symbol**: Kürzel bei Yahoo Finance. Du findest es auf **finance.yahoo.com**, es steht in Klammern hinter dem Namen. Schweizer Titel enden auf `.SW`, z. B. Nestlé `NESN.SW`, Novartis `NOVN.SW`, Roche GS `ROP.SW`, UBS `UBSG.SW`
- **Hinzufügen:** einen ganzen Block kopieren und anpassen. **Entfernen:** den Block löschen.
- News-Quellen funktionieren gleich (`[[news]]` mit `name`, `url`, `gruppe`, bei englischen Quellen `sprache = "en"`).

**Wichtig:** Die lokale Datei und die Datei auf GitHub sind zwei getrennte Kopien.
- **Lokal:** Datei speichern, dann das schwarze Fenster schliessen und `start.bat` neu starten.
- **Handy-Version:** auf github.com im Repository `einstellungen.toml` anklicken → Stift-Symbol ✏️ (*Edit*) → ändern → grüner Knopf **Commit changes…** → nochmals **Commit changes**. Ab dem nächsten Daten-Update (max. 30 Min.) gilt die Änderung.

---

## 3. Einmalig: Handy-Version auf GitHub einrichten

### Schritt A – GitHub-Konto erstellen
1. Gehe auf **github.com** und klicke oben rechts auf **Sign up**.
2. E-Mail, Passwort und einen Benutzernamen eingeben (z. B. `tobi-briefing`). Der Benutzername erscheint später in der Adresse der App.
3. Den Code aus der Bestätigungs-E-Mail eingeben. Bei «Plan» den kostenlosen **Free**-Plan wählen.

### Schritt B – Repository (Projektordner) erstellen
1. Oben rechts auf **+** → **New repository** klicken.
2. **Repository name:** `morning-briefing`
3. **Public** auswählen. Das ist nötig, damit GitHub Pages kostenlos ist.
4. Die übrigen Häkchen (README usw.) **nicht** setzen.
5. Unten auf **Create repository** klicken.

### Schritt C – Dateien hochladen
1. Auf der neuen, leeren Seite auf den Link **uploading an existing file** klicken.
2. Im Windows-Explorer den Ordner *Claudecode_Morning Briefing* öffnen und **alle Dateien und Ordner darin** markieren (Ctrl+A).
   Das sind: `.github`, `docs`, `app.py`, `daten.py`, `einstellungen.toml`, `requirements.txt`, `start.bat`, `ANLEITUNG.md`, `.gitignore`.
3. Alles zusammen ins Browser-Fenster auf die Fläche *Drag files here* ziehen. Warten, bis alle Dateien aufgelistet sind.
4. Unten auf den grünen Knopf **Commit changes** klicken.
5. Kontrolle: In der Dateiliste müssen die Ordner **`.github`** und **`docs`** erscheinen.

### Schritt D – GitHub Pages einschalten (macht die Webseite öffentlich erreichbar)
1. Im Repository oben auf **Settings** (Zahnrad) klicken.
2. Links im Menü **Pages** wählen.
3. Bei **Source:** «Deploy from a branch» auswählen.
4. Bei **Branch:** `main` und daneben den Ordner **`/docs`** wählen → **Save**.
5. 1–2 Minuten warten und die Seite neu laden. Oben erscheint
   **«Your site is live at https://BENUTZERNAME.github.io/morning-briefing/»**. Das ist die Adresse deiner App.

### Schritt E – Automatische Daten-Updates starten
1. Im Repository oben auf **Actions** klicken.
2. Falls ein Hinweis erscheint: **I understand my workflows, go ahead and enable them** klicken.
3. Links **Daten aktualisieren** wählen → rechts **Run workflow** → grüner Knopf **Run workflow**.
4. Nach ca. 1 Minute erscheint ein grüner Haken ✅. Ab jetzt läuft das werktags automatisch alle 30 Minuten.
   Ein rotes ✖ bedeutet einen Fehler. Darauf klicken, dann siehst du die Details.

---

## 4. App auf dem Handy installieren

### iPhone (Safari)
1. Die Adresse `https://BENUTZERNAME.github.io/morning-briefing/` in **Safari** öffnen.
2. Unten auf das **Teilen-Symbol** tippen (Quadrat mit Pfeil nach oben).
3. Nach unten scrollen und **Zum Home-Bildschirm** antippen.
4. Oben rechts auf **Hinzufügen** tippen.
   Auf dem Home-Bildschirm erscheint das Sonnen-Symbol «Briefing». Die App startet im Vollbild.

### Android (Chrome)
1. Die Adresse in **Chrome** öffnen.
2. Oben rechts auf **⋮** (drei Punkte) tippen.
3. **App installieren** wählen (bei manchen Geräten: *Zum Startbildschirm hinzufügen*) → **Installieren**.

---

## 5. Wenn etwas nicht klappt
- **«nicht verfügbar»** bei einem Wert: Die Quelle hat nicht geantwortet oder das Kürzel stimmt nicht.
- **«Offline – du siehst die zuletzt geladenen Daten …»**: Es besteht keine Internetverbindung. Die App zeigt die letzten Daten an.
- **Lokal: rote Meldung «Daten konnten nicht geladen werden»**: Das schwarze Fenster ist zu. `start.bat` neu starten.
- **Handy-Daten sind alt**: Auf GitHub unter **Actions** prüfen, ob die letzten Läufe grün sind. Abends, am Wochenende und in der Nacht gibt es bewusst keine Updates.
- **Handy-App zeigt nach einer Änderung noch das alte Design:** die App einmal ganz schliessen und neu öffnen.

## Gut zu wissen
- Kurse von Yahoo Finance sind teils ca. 15 Min. verzögert. Die Veränderung bezieht sich auf den letzten Schlusskurs. Die Zinsen stammen von SNB, Bundesbank und Yahoo und werden einmal täglich aktualisiert.
- «Schluss Fr 02.10.» bedeutet: Dieser Markt hat heute noch nicht gehandelt.
- Die öffentliche Version enthält nur Kurse, Schlagzeilen und Links, keine persönlichen Daten. Es gibt keine Passwörter oder Schlüssel im Code.
- GitHub-Zeitpläne können 5–15 Minuten Verspätung haben.
