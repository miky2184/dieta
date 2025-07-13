const CACHE_NAME = 'menu-dieta-v1';
const STATIC_CACHE = [
  '/static/css/bootstrap.min.css',
  '/static/js/bootstrap.bundle.min.js',
  '/static/css/pwa-styles.css',
  '/static/js/pwa-installer.js',
  '/static/icons/icon-192x192.png'
];

// Installazione - cacha solo risorse statiche
self.addEventListener('install', function(event) {
  console.log('Service Worker: Installing...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        console.log('Service Worker: Caching static files');
        return cache.addAll(STATIC_CACHE);
      })
      .then(() => self.skipWaiting())
  );
});

// Attivazione
self.addEventListener('activate', function(event) {
  console.log('Service Worker: Activating...');
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames.map(function(cacheName) {
          if (cacheName !== CACHE_NAME) {
            console.log('Service Worker: Deleting old cache', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch - solo per risorse statiche
self.addEventListener('fetch', function(event) {
  // Solo per richieste GET di risorse statiche
  if (event.request.method !== 'GET') {
    return;
  }

  // Solo per file statici (CSS, JS, immagini)
  if (event.request.url.includes('/static/')) {
    event.respondWith(
      caches.match(event.request)
        .then(function(response) {
          // Se in cache, restituisci dalla cache
          if (response) {
            return response;
          }

          // Altrimenti fetch e aggiungi alla cache
          return fetch(event.request).then(function(response) {
            // Controlla se la risposta è valida
            if (!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }

            // Clona e aggiungi alla cache
            var responseToCache = response.clone();
            caches.open(CACHE_NAME)
              .then(function(cache) {
                cache.put(event.request, responseToCache);
              });

            return response;
          });
        })
    );
  }
});