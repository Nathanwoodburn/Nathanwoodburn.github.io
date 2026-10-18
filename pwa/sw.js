// Service Worker for Nathan.Woodburn/ PWA with network-first navigation and offline fallback

const CACHE_NAME = "pwabuilder-offline-v3";

const PRECACHE_ASSETS = [
  "/",
  "/assets/bootstrap/css/bootstrap.min.css",
  "/assets/css/styles.min.css",
  "/assets/css/layout.css",
  "/assets/css/navbar.css",
  "/assets/bootstrap/js/bootstrap.min.js",
  "/assets/js/script.min.js",
  "/assets/img/favicon/favicon-16x16.png",
  "/assets/img/favicon/android-chrome-192x192.png"
];

self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});

self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRECACHE_ASSETS).catch((err) => {
        console.warn("Failed to precache some assets during install:", err);
      });
    })
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    Promise.all([
      self.clients.claim(),
      caches.keys().then((keys) => {
        return Promise.all(
          keys.map((key) => {
            if (key !== CACHE_NAME) {
              return caches.delete(key);
            }
          })
        );
      })
    ])
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") {
    return;
  }

  const url = new URL(event.request.url);

  // Never intercept or cache API or Spotify requests
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/spotify")) {
    return;
  }

  // Handle page navigations with Network-First strategy
  if (event.request.mode === "navigate") {
    event.respondWith(
      fetch(event.request).catch(async () => {
        const cache = await caches.open(CACHE_NAME);
        const cachedHome = await cache.match("/");
        if (cachedHome) {
          return cachedHome;
        }
        return new Response("Offline", {
          status: 503,
          statusText: "Service Unavailable",
          headers: { "Content-Type": "text/plain" }
        });
      })
    );
    return;
  }

  // Fallback to precached static assets when offline
  if (url.origin === self.location.origin && url.pathname.startsWith("/assets/")) {
    event.respondWith(
      fetch(event.request).catch(async () => {
        const cache = await caches.open(CACHE_NAME);
        const cachedAsset = await cache.match(event.request, { ignoreSearch: true });
        if (cachedAsset) {
          return cachedAsset;
        }
        return new Response("", { status: 408, statusText: "Request Timeout" });
      })
    );
  }
});
