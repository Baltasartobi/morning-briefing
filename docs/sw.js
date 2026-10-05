/* ================================================================
   Service Worker – macht die App installierbar und offline nutzbar.
   App-Dateien: aus dem Speicher, im Hintergrund aktualisiert.
   data.json:   immer zuerst aus dem Netz, bei Offline die letzte Version.
   Bei Änderungen an index.html/style.css/app.js: VERSION erhöhen.
   ================================================================ */

const VERSION = "mb-v1";
const APP_DATEIEN = [
  "./",
  "index.html",
  "style.css",
  "app.js",
  "manifest.json",
  "icons/icon-192.png",
  "icons/icon-512.png",
  "icons/apple-touch-icon.png",
  "icons/favicon-32.png",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(APP_DATEIEN)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((namen) => Promise.all(namen.filter((n) => n !== VERSION).map((n) => caches.delete(n))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;

  // Daten: Netz zuerst, sonst gespeicherte Version
  if (url.pathname.endsWith("/data.json")) {
    e.respondWith(
      fetch(e.request)
        .then((antwort) => {
          const kopie = antwort.clone();
          caches.open(VERSION).then((c) => c.put("data.json", kopie));
          return antwort;
        })
        .catch(() => caches.match("data.json"))
    );
    return;
  }

  // App-Dateien: sofort aus dem Speicher, im Hintergrund auffrischen
  e.respondWith(
    caches.match(e.request, { ignoreSearch: true }).then((gespeichert) => {
      const netz = fetch(e.request)
        .then((antwort) => {
          if (antwort.ok) {
            const kopie = antwort.clone();
            caches.open(VERSION).then((c) => c.put(e.request, kopie));
          }
          return antwort;
        })
        .catch(() => gespeichert);
      return gespeichert || netz;
    })
  );
});
