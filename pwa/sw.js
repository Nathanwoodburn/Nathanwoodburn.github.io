// This is the service worker with the combined offline experience (Offline page + Offline copy of pages)

const CACHE = "pwabuilder-offline-page";

importScripts('https://storage.googleapis.com/workbox-cdn/releases/5.1.2/workbox-sw.js');

const PRECACHE_ASSETS = [
  '/',
  '/404',
  '/assets/bootstrap/css/bootstrap.min.css',
  'https://fonts.googleapis.com/css?family=Lora:400,700,400italic,700italic&display=swap',
  'https://fonts.googleapis.com/css?family=Cabin:700&display=swap',
  'https://fonts.googleapis.com/css?family=Anonymous+Pro&display=swap',
  'https://fonts.googleapis.com/css?family=Roboto:300,400,500,700',
  '/assets/css/styles.min.css',
  '/assets/css/404.min.css',
  '/assets/css/profile.min.css',
  '/assets/bootstrap/js/bootstrap.min.js',
  '/assets/js/script.min.js',
  '/assets/js/404.min.js',
  '/assets/img/favicon/favicon-16x16.png',
  '/assets/img/favicon/android-chrome-192x192.png'
]


self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});

self.addEventListener('install', async (event) => {
  event.waitUntil(
    caches.open(CACHE)
      .then((cache) => cache.addAll(PRECACHE_ASSETS))
  );
});

if (workbox.navigationPreload.isSupported()) {
  workbox.navigationPreload.enable();
}

workbox.routing.registerRoute(
  new RegExp('/*'),
  new workbox.strategies.StaleWhileRevalidate({
    cacheName: CACHE
  })
);

self.addEventListener('fetch', (event) => {
  if (event.request.mode === 'navigate') {
    event.respondWith((async () => {
      try {
        const preloadResp = await event.preloadResponse;

        if (preloadResp) {
          return preloadResp;
        }

        const networkResp = await fetch(event.request);
        return networkResp;
      } catch (error) {

        const cache = await caches.open(CACHE);
        const cachedResp = await cache.match('/404');
        return cachedResp;
      }
    })());
  }
});