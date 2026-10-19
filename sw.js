/* Kira Defteri: uygulamayı internetsiz açılabilir yapar. tufe.json her zaman önce internetten denenir. */
const CACHE = "kira-defteri-v1.8.1";
const CORE = ["./", "index.html", "manifest.webmanifest", "icons/icon.svg", "icons/icon-192.png", "icons/icon-512.png", "icons/apple-touch-icon.png", "tufe.json"];
/* version.json hiç önbelleğe alınmaz: güncelleme kontrolü her zaman sunucuya sorar */

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(CORE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  if (new URL(req.url).pathname.endsWith("/version.json")) return;
  const url = new URL(req.url);
  const sameOrigin = url.origin === location.origin;
  const isPage = req.mode === "navigate" || url.pathname.endsWith("/index.html");
  const isTufe = sameOrigin && url.pathname.endsWith("/tufe.json");

  if (isPage || isTufe) {
    /* önce internet, olmazsa kayıtlı kopya: güncellemeler hemen gelir */
    e.respondWith(
      fetch(req, { cache: "no-cache" }).then(res => {
        if (res.ok) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(isTufe ? "tufe.json" : "index.html", copy)); }
        return res;
      }).catch(() => caches.match(isTufe ? "tufe.json" : "index.html"))
    );
    return;
  }
  if (sameOrigin || url.hostname === "cdnjs.cloudflare.com" || url.hostname === "cdn.sheetjs.com" || (url.hostname === "www.gstatic.com" && url.pathname.startsWith("/firebasejs/"))) {
    e.respondWith(
      caches.match(req).then(hit => hit || fetch(req).then(res => {
        if (res.ok) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); }
        return res;
      }))
    );
  }
});
