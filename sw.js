// Goalie - Production PWA Service Worker (v3.2.0)
const CACHE_NAME = 'goalie-cache-v3.2.0';
const STATIC_ASSETS = [
    './',
    'index.html',
    'login.html',
    'admin.html',
    'manifest.json',
    'favicon.ico',
    'apple-touch-icon.png',
    'logo.svg',
    'public/logo.svg',
    'public/icons/goalie-logo.svg',
    'public/icons/pwa/icon-192x192.png',
    'public/icons/pwa/icon-512x512.png',
    'public/css/tailwind.min.css',
    'public/js/db.js',
    'public/js/garmin_map_viewer.js',
    'public/vendor/leaflet/leaflet.js',
    'public/vendor/leaflet/leaflet.css'
];

// Install: Cache shell assets
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(STATIC_ASSETS).catch((err) => {
                console.warn('[SW] Caching non-critical asset failed:', err);
            });
        })
    );
    self.skipWaiting();
});

// Activate: Clean up legacy caches immediately and claim clients
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.map((key) => {
                    if (key !== CACHE_NAME) {
                        console.log('[SW] Deleting legacy cache:', key);
                        return caches.delete(key);
                    }
                })
            );
        })
    );
    self.clients.claim();
});

// Communication channel for forced update / cache eviction
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
    if (event.data && event.data.type === 'PURGE_OLD_CACHES') {
        caches.keys().then((keys) => {
            return Promise.all(
                keys.map((key) => {
                    if (key !== CACHE_NAME) {
                        return caches.delete(key);
                    }
                })
            );
        });
    }
});

// Fetch: Network-First for HTML navigation, Stale-While-Revalidate for static assets
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // Bypass non-GET requests and API calls (let them go directly to network)
    if (event.request.method !== 'GET' || url.pathname.includes('/api/')) {
        return;
    }

    const isHtmlNavigation = event.request.mode === 'navigate' || 
        (event.request.headers.get('accept') && event.request.headers.get('accept').includes('text/html'));

    if (isHtmlNavigation) {
        // Network-First for HTML documents to guarantee freshest deploy, fallback to cache if offline
        event.respondWith(
            fetch(event.request)
                .then((networkResponse) => {
                    if (networkResponse && networkResponse.status === 200) {
                        const responseClone = networkResponse.clone();
                        caches.open(CACHE_NAME).then((cache) => {
                            cache.put(event.request, responseClone);
                        });
                    }
                    return networkResponse;
                })
                .catch(() => {
                    return caches.match(event.request).then((cached) => {
                        return cached || caches.match('index.html') || caches.match('./') || caches.match('/');
                    });
                })
        );
        return;
    }

    // Stale-While-Revalidate for static assets (CSS, JS, fonts, icons)
    event.respondWith(
        caches.match(event.request).then((cachedResponse) => {
            const fetchPromise = fetch(event.request).then((networkResponse) => {
                if (networkResponse && networkResponse.status === 200) {
                    const responseClone = networkResponse.clone();
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(event.request, responseClone);
                    });
                }
                return networkResponse;
            }).catch(() => null);

            return cachedResponse || fetchPromise;
        })
    );
});
