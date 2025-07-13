// Service Worker Sicuro - app/static/sw.js
const CACHE_NAME = 'menu-dieta-v1';

// Cache SOLO i file che sicuramente esistono
const STATIC_CACHE = [
  // Manifest e icone che sappiamo esistono
  '/manifest.json',
  '/static/icons/android-icon-192x192.png',
  '/static/icons/android-icon-144x144.png'
  // NON includiamo CSS/JS che potrebbero non esistere
];

// Installazione - cache solo se i file esistono
self.addEventListener('install', function(event) {
  console.log('Service Worker: Installing...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        console.log('Service Worker: Caching essential files');
        // Cache solo file essenziali, uno alla volta per evitare errori
        return Promise.all(
          STATIC_CACHE.map(url => {
            return fetch(url)
              .then(response => {
                if (response.ok) {
                  return cache.put(url, response);
                } else {
                  console.warn(`Service Worker: Skipping ${url} - not found`);
                }
              })
              .catch(error => {
                console.warn(`Service Worker: Failed to cache ${url}:`, error);
              });
          })
        );
      })
      .then(() => {
        console.log('Service Worker: Installation complete');
        return self.skipWaiting();
      })
      .catch(error => {
        console.error('Service Worker: Installation failed:', error);
      })
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
    }).then(() => {
      console.log('Service Worker: Activation complete');
      return self.clients.claim();
    })
  );
});

// Fetch - versione molto semplice e sicura
self.addEventListener('fetch', function(event) {
  // Solo per richieste GET
  if (event.request.method !== 'GET') {
    return;
  }

  // Solo per risorse del nostro dominio
  if (!event.request.url.startsWith(self.location.origin)) {
    return;
  }

  // Solo per file statici
  if (event.request.url.includes('/static/') ||
      event.request.url.endsWith('/manifest.json')) {

    event.respondWith(
      caches.match(event.request)
        .then(function(response) {
          // Se in cache, usa la cache
          if (response) {
            console.log('Service Worker: Serving from cache:', event.request.url);
            return response;
          }

          // Altrimenti fetch normalmente
          console.log('Service Worker: Fetching:', event.request.url);
          return fetch(event.request)
            .then(function(response) {
              // Se la risposta è OK, aggiungi alla cache
              if (response && response.status === 200 && response.type === 'basic') {
                var responseToCache = response.clone();
                caches.open(CACHE_NAME)
                  .then(function(cache) {
                    cache.put(event.request, responseToCache);
                  })
                  .catch(error => {
                    console.warn('Service Worker: Failed to cache response:', error);
                  });
              }
              return response;
            })
            .catch(error => {
              console.warn('Service Worker: Fetch failed:', error);
              return response; // Fallback alla cache se fetch fallisce
            });
        })
        .catch(error => {
          console.warn('Service Worker: Cache match failed:', error);
          // Fallback a fetch normale
          return fetch(event.request);
        })
    );
  }
});

// Error handler globale
self.addEventListener('error', function(event) {
  console.error('Service Worker: Global error:', event.error);
});

self.addEventListener('unhandledrejection', function(event) {
  console.error('Service Worker: Unhandled promise rejection:', event.reason);
});

console.log('Service Worker: Script loaded successfully');