/* FloodShield service worker: offline app shell + offline Emergency Guide.
   Bump VERSION when you change cached files so phones pick up the update. */
const VERSION = "fs-v2";
const SHELL = ["/", "/style.css", "/app.js", "/config.js", "/manifest.webmanifest", "/icons/icon-192.png", "/api/guide"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(VERSION).then(c => Promise.allSettled(SHELL.map(u => c.add(u)))).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== VERSION).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
const put = (req, res) => {
  if (res && (res.ok || res.type === "opaque")) caches.open(VERSION).then(c => c.put(req, res.clone()));
  return res;
};
self.addEventListener("fetch", e => {
  const r = e.request;
  if (r.method !== "GET") return;
  const u = new URL(r.url);
  if (u.origin === location.origin) {
    // Live data (/api/*) always goes to the network, except the emergency guide which is cached.
    if (u.pathname.startsWith("/api/") && u.pathname !== "/api/guide") return;
    e.respondWith(fetch(r).then(res => put(r, res)).catch(() =>
      caches.match(r).then(m => m || (r.mode === "navigate" ? caches.match("/") : Response.error()))));
    return;
  }
  if (u.hostname === "cdnjs.cloudflare.com") {   // map library
    e.respondWith(caches.match(r).then(m => m || fetch(r).then(res => put(r, res))));
  }
});
