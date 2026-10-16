// Goalie — Production PWA Service Worker (v2.4.1)
const CACHE_NAME = 'goalie-cache-v2.4.1';
const STATIC_ASSETS = [
    '/',
    '/index.html',
    '/login.html',
    '/admin.html',
    '/manifest.json',
    '/favicon.ico',
    '/apple-touch-icon.png',
    '/public/icons/pwa/icon-192x192.png',
    '/public/icons/pwa/icon-512x512.png',
    'https://api.fontshare.com/v2/css?f[]=general-sans@400,500,600,700&display=swap',
    'https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,700;1,9..40,400&family=JetBrains+Mono:wght@400;500&display=swap',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css',
    'https://cdn.tailwindcss.com'
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

// Activate: Clean up legacy caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.map((key) => {
                    if (key !== CACHE_NAME) {
                        return caches.delete(key);
                    }
                })
            );
        })
    );
    self.clients.claim();
});

// Fetch: Stale-While-Revalidate for UI assets, Network-First for API
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // Bypass non-GET requests and API calls (let them go directly to network)
    if (event.request.method !== 'GET' || url.pathname.startsWith('/api/')) {
        return;
    }

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
            }).catch(() => {
                // If offline and request is an HTML page, fallback to cached index.html
                if (event.request.headers.get('accept') && event.request.headers.get('accept').includes('text/html')) {
                    return caches.match('/index.html') || caches.match('/');
                }
            });

            return cachedResponse || fetchPromise;
        })
    );
});
