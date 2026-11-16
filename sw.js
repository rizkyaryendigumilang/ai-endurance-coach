// Goalie - Production PWA Service Worker (v4.0.0)
const CACHE_NAME = 'goalie-cache-v4.0.0';

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
    'public/icons/pwa/apple-touch-icon.png',
    'public/icons/pwa/favicon-32x32.png',
    'public/icons/pwa/favicon-16x16.png',
    'public/css/tailwind.min.css',
    'public/js/db.js',
    'public/js/garmin_workouts_data.js',
    'public/js/garmin_map_viewer.js',
    'public/js/modules/sports-math.js',
    'public/js/modules/settings-controller.js',
    'public/js/modules/map-elevation-scrubber.js',
    'public/js/modules/mobile-native.js',
    'public/js/modules/enterprise-hub.js',
    'public/js/modules/garmin-sync-manager.js',
    'public/js/modules/calendar-widget.js',
    'public/vendor/leaflet/leaflet.js',
    'public/vendor/leaflet/leaflet.css',
    'public/vendor/chartjs/chart.umd.min.js'
];

// Install: Cache critical shell assets resiliently
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(async (cache) => {
            for (const asset of STATIC_ASSETS) {
                try {
                    await cache.add(asset);
                } catch (err) {
                    console.warn('[SW] Non-critical asset cache skipped:', asset, err);
                }
            }
        })
    );
    self.skipWaiting();
});

// Activate: Delete old cache generations and claim clients immediately
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.map((key) => {
                    if (key !== CACHE_NAME) {
                        console.log('[SW] Evicting legacy cache bucket:', key);
                        return caches.delete(key);
                    }
                })
            );
        }).then(() => self.clients.claim())
    );
});

// Message channel: Skip waiting or cache purge requests
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

// Fetch router: Intelligent offline routing
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // Bypass non-GET requests (e.g. POST, PUT, DELETE)
    if (event.request.method !== 'GET') {
        return;
    }

    // 1. API Requests: Network-First with graceful offline fallback
    if (url.pathname.includes('/api/')) {
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
                .catch(async () => {
                    const cached = await caches.match(event.request);
                    if (cached) {
                        return cached;
                    }
                    return new Response(JSON.stringify({
                        offline: true,
                        status: 'offline',
                        message: 'Aplikasi sedang offline. Menggunakan data tersimpan lokal.'
                    }), {
                        status: 503,
                        headers: { 'Content-Type': 'application/json' }
                    });
                })
        );
        return;
    }

    // 2. HTML Navigation: Network-First to guarantee newest release, fallback to index.html
    const isHtmlNavigation = event.request.mode === 'navigate' || 
        (event.request.headers.get('accept') && event.request.headers.get('accept').includes('text/html'));

    if (isHtmlNavigation) {
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

    // 3. Static Assets (CSS, JS, Fonts, Images): Stale-While-Revalidate
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
