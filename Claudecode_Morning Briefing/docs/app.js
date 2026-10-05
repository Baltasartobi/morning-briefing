/* ================================================================
   Morning Briefing – Logik der Seite
   Lokal (start.bat):   Daten kommen frisch von /api/briefing
   Online (GitHub):     Daten kommen aus data.json (alle 30 Min. erneuert)
   ================================================================ */

const LOKAL = ["localhost", "127.0.0.1"].includes(location.hostname);
const WOCHENTAGE = ["So", "Mo", "Di", "Mi", "Do", "Fr", "Sa"];
const $ = (id) => document.getElementById(id);

const zustand = { daten: null, filter: { typ: "alle", wert: "" } };

// ---------------------------------------------------------------- kleine Helfer

function speichern(schluessel, wert) { try { localStorage.setItem(schluessel, wert); } catch (e) {} }
function lesen(schluessel) { try { return localStorage.getItem(schluessel); } catch (e) { return null; } }

function esc(text) {
  return String(text ?? "").replace(/[&<>"']/g, (z) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[z]));
}

// Schweizer Zahlenformat, z. B. 13'722.98 (je nach Browser liefert Intl ’ – vereinheitlicht auf ')
function zahl(wert, dezimalen = 2) {
  return new Intl.NumberFormat("de-CH", { minimumFractionDigits: dezimalen, maximumFractionDigits: dezimalen })
    .format(wert).replace(/[’’]/g, "'");
}

function vorzeichen(wert, text) {
  return (wert > 0 ? "+" : wert < 0 ? "−" : "±") + text;
}

function richtung(wert, schwelle = 0.005) {
  return wert > schwelle ? "plus" : wert < -schwelle ? "minus" : "neutral";
}

function zweistellig(n) { return String(n).padStart(2, "0"); }
function uhrzeit(d) { return `${zweistellig(d.getHours())}:${zweistellig(d.getMinutes())}`; }
function kurzDatum(d) { return `${WOCHENTAGE[d.getDay()]} ${zweistellig(d.getDate())}.${zweistellig(d.getMonth() + 1)}.`; }

function gleicherTag(a, b) { return a.toDateString() === b.toDateString(); }

function wannText(iso, mitZeit = true) {
  if (!iso) return "";
  const d = new Date(iso);
  const heute = new Date();
  const gestern = new Date(); gestern.setDate(heute.getDate() - 1);
  if (gleicherTag(d, heute)) return uhrzeit(d);
  if (gleicherTag(d, gestern)) return mitZeit ? `gestern ${uhrzeit(d)}` : "gestern";
  return kurzDatum(d);
}

// Datum ohne Uhrzeit (z. B. Schlusskurs) → «heute» oder «Schluss Fr 02.10.»
function standText(datum) {
  if (!datum) return "";
  const d = new Date(datum + "T12:00:00");
  return gleicherTag(d, new Date()) ? "heute" : "Schluss " + kurzDatum(d);
}

// Mini-Verlauf der letzten Tage als SVG
function sparkline(werte) {
  if (!werte || werte.length < 2) return `<svg class="spark" viewBox="0 0 60 26" aria-hidden="true"></svg>`;
  const min = Math.min(...werte), max = Math.max(...werte);
  const spanne = max - min || 1;
  const punkte = werte.map((w, i) => [
    (i / (werte.length - 1)) * 56 + 2,
    24 - ((w - min) / spanne) * 22,
  ]);
  const [lx, ly] = punkte[punkte.length - 1];
  return `<svg class="spark" viewBox="0 0 60 26" aria-hidden="true">
    <polyline points="${punkte.map((p) => p.map((n) => n.toFixed(1)).join(",")).join(" ")}"/>
    <circle cx="${lx.toFixed(1)}" cy="${ly.toFixed(1)}" r="2.2"/>
  </svg>`;
}

// ---------------------------------------------------------------- Bausteine

function kursZeile(k) {
  if (!k.verfuegbar) {
    return `<div class="zeile"><div><div class="z-name">${esc(k.name)}</div><div class="z-sub">&nbsp;</div></div>
      ${sparkline(null)}<div class="z-rechts"><div class="z-wert na">nicht verfügbar</div></div></div>`;
  }
  const r = richtung(k.veraenderung_pct);
  const sub = [k.einheit, standText(k.datum)].filter(Boolean).join(" · ");
  return `<div class="zeile">
    <div><div class="z-name" title="${esc(k.symbol)}">${esc(k.name)}</div><div class="z-sub">${esc(sub)}</div></div>
    ${sparkline(k.verlauf)}
    <div class="z-rechts">
      <div class="z-wert">${zahl(k.kurs, k.dezimalen)}</div>
      <div class="z-pct ${r}">${vorzeichen(k.veraenderung_pct, zahl(Math.abs(k.veraenderung_pct)) + "%")}</div>
    </div>
  </div>`;
}

function zinsZeile(z) {
  if (!z.verfuegbar) {
    return `<div class="zeile"><div><div class="z-name">${esc(z.name)}</div><div class="z-sub">&nbsp;</div></div>
      ${sparkline(null)}<div class="z-rechts"><div class="z-wert na">nicht verfügbar</div></div></div>`;
  }
  const quelle = { snb: "SNB", bundesbank: "Bundesbank", yahoo: "Yahoo" }[z.quelle] || "";
  return `<div class="zeile">
    <div><div class="z-name">${esc(z.name)}</div><div class="z-sub">${esc([quelle, standText(z.datum)].filter(Boolean).join(" · "))}</div></div>
    ${sparkline(z.verlauf)}
    <div class="z-rechts">
      <div class="z-wert">${zahl(z.wert, 2)}%</div>
      <div class="z-pct neutral">${vorzeichen(z.veraenderung_bp, zahl(Math.abs(z.veraenderung_bp), 1) + " BP")}</div>
    </div>
  </div>`;
}

function newsEintrag(a) {
  const en = a.sprache === "en" ? `<span class="tag" title="Englisch">EN</span>` : "";
  return `<a class="news-item" href="${esc(a.link)}" target="_blank" rel="noopener">
    <div class="n-meta"><span class="n-quelle">${esc(a.quelle)}</span><span>·</span><span>${esc(wannText(a.zeit))}</span>${en}</div>
    <div class="n-titel">${esc(a.titel)}</div>
  </a>`;
}

function skelette(anzahl) {
  return Array.from({ length: anzahl }, (_, i) => `<div class="skel ${i % 2 ? "kurz" : ""}"></div>`).join("");
}

// ---------------------------------------------------------------- Darstellung

function newsFiltern(artikel) {
  const { typ, wert } = zustand.filter;
  if (typ === "gruppe") return artikel.filter((a) => a.gruppe === wert);
  if (typ === "quelle") return artikel.filter((a) => a.quelle === wert);
  return artikel;
}

function filterZeichnen() {
  const d = zustand.daten;
  if (!d) return;
  const gruppen = [...new Set(d.news.quellen.map((q) => q.gruppe).filter(Boolean))];
  const chips = [
    { typ: "alle", wert: "", text: "Alle" },
    ...gruppen.map((g) => ({ typ: "gruppe", wert: g, text: g })),
    ...d.news.quellen.map((q) => ({ typ: "quelle", wert: q.name, text: q.name + (q.verfuegbar ? "" : " (nicht verfügbar)") })),
  ];
  $("filter").innerHTML = chips.map((c) => {
    const aktiv = c.typ === zustand.filter.typ && c.wert === zustand.filter.wert;
    return `<button type="button" class="chip" data-typ="${c.typ}" data-wert="${esc(c.wert)}" aria-pressed="${aktiv}">${esc(c.text)}</button>`;
  }).join("");

  const liste = newsFiltern(d.news.artikel);
  $("news").innerHTML = liste.length ? liste.map(newsEintrag).join("") : `<div class="leer">Keine Schlagzeilen verfügbar.</div>`;
}

function zeichnen() {
  const d = zustand.daten;
  if (!d) return;

  $("kernaussagen").innerHTML = d.kernaussagen.length
    ? d.kernaussagen.map((s) => `<li>${esc(s)}</li>`).join("")
    : `<li class="na">Keine Kurse verfügbar.</li>`;
  $("maerkte").innerHTML = d.maerkte.map(kursZeile).join("");
  $("devisen").innerHTML = d.devisen_rohstoffe.map(kursZeile).join("");
  $("zinsen").innerHTML = d.zinsen.map(zinsZeile).join("");
  $("watchlist").innerHTML = d.watchlist.length
    ? d.watchlist.map(kursZeile).join("")
    : `<div class="leer">Noch keine Titel – siehe einstellungen.toml.</div>`;
  const neueste = d.news.artikel.slice(0, 5);
  $("news-kurz").innerHTML = neueste.length ? neueste.map(newsEintrag).join("") : `<div class="leer">Keine Schlagzeilen verfügbar.</div>`;
  filterZeichnen();

  const stand = new Date(d.aktualisiert);
  $("stand").textContent = "Stand " + (gleicherTag(stand, new Date()) ? uhrzeit(stand) : `${kurzDatum(stand)} ${uhrzeit(stand)}`);
}

function hinweis(text, art = "") {
  $("hinweis").innerHTML = text ? `<div class="hinweis ${art}">${text}</div>` : "";
}

// ---------------------------------------------------------------- Daten laden

async function laden(neu = false) {
  const knopf = $("aktualisieren");
  knopf.classList.add("dreht");
  knopf.disabled = true;
  try {
    const url = LOKAL ? "/api/briefing" + (neu ? "?neu=1" : "") : "data.json?t=" + Date.now();
    const antwort = await fetch(url, { cache: "no-store" });
    if (!antwort.ok) throw new Error("HTTP " + antwort.status);
    zustand.daten = await antwort.json();
    speichern("mb-daten", JSON.stringify(zustand.daten));
    hinweis("");
    zeichnen();
  } catch (fehler) {
    const gespeichert = lesen("mb-daten");
    if (gespeichert && !zustand.daten) {
      try { zustand.daten = JSON.parse(gespeichert); zeichnen(); } catch (e) {}
    }
    if (zustand.daten) {
      const stand = new Date(zustand.daten.aktualisiert);
      hinweis(`Offline – du siehst die zuletzt geladenen Daten von ${kurzDatum(stand)} ${uhrzeit(stand)}.`);
    } else {
      hinweis(LOKAL
        ? "Daten konnten nicht geladen werden. Läuft das schwarze App-Fenster noch? Sonst start.bat erneut doppelklicken."
        : "Daten konnten nicht geladen werden. Bitte Internetverbindung prüfen und erneut versuchen.", "fehler");
    }
  } finally {
    knopf.classList.remove("dreht");
    knopf.disabled = false;
  }
}

// ---------------------------------------------------------------- Bedienung

function tabWechseln(tab) {
  document.body.dataset.tab = tab;
  document.querySelectorAll(".tabs button").forEach((b) => {
    if (b.dataset.tab === tab) b.setAttribute("aria-current", "page"); else b.removeAttribute("aria-current");
  });
  speichern("mb-tab", tab);
  window.scrollTo({ top: 0 });
}

document.querySelectorAll(".tabs button").forEach((b) => b.addEventListener("click", () => tabWechseln(b.dataset.tab)));
document.querySelectorAll("[data-gehe-zu]").forEach((b) => b.addEventListener("click", () => tabWechseln(b.dataset.geheZu)));

$("filter").addEventListener("click", (e) => {
  const chip = e.target.closest(".chip");
  if (!chip) return;
  zustand.filter = { typ: chip.dataset.typ, wert: chip.dataset.wert };
  filterZeichnen();
});

$("theme").addEventListener("click", () => {
  const jetzt = document.documentElement.dataset.theme
    || (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
  const neu = jetzt === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = neu;
  speichern("mb-theme", neu);
});

$("aktualisieren").addEventListener("click", () => laden(true));

// Beim Zurückkehren in die App (z. B. Handy) automatisch neu laden, wenn älter als 10 Minuten
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible" && zustand.daten
      && Date.now() - new Date(zustand.daten.aktualisiert).getTime() > 10 * 60 * 1000) laden(false);
});

// ---------------------------------------------------------------- Start

$("datum").textContent = new Date().toLocaleDateString("de-CH", { weekday: "long", day: "numeric", month: "long" });
tabWechseln(lesen("mb-tab") || "uebersicht");
["kernaussagen", "maerkte", "devisen", "zinsen", "watchlist", "news-kurz", "news"].forEach((id) => { $(id).innerHTML = skelette(id === "kernaussagen" ? 3 : 4); });
laden(false);

// Installierbare App (nur online; lokal würde der Speicher beim Entwickeln stören)
if ("serviceWorker" in navigator && !LOKAL) {
  navigator.serviceWorker.register("sw.js").catch(() => {});
}
