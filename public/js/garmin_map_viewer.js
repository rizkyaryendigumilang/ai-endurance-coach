/**
 * Garmin Connect Real GPS Map & Telemetry Engine (Leaflet)
 * Goalie AI Endurance Coach - High Performance Modular Engine
 */
(function(window) {
    'use strict';

let activityMapInstance = null;
        let currentMapTileLayer = null;
        let currentMapPolyline = null;
        let currentMapGlow = null;
        let currentMapMarkers = [];
        let currentModalRouteCoords = [];
        let currentModalDistanceKm = 0;
        let replayAnimationTimer = null;
        let replayCurrentIndex = 0;
        let replayRunnerMarker = null;
        let activeMapStyle = 'outdoor'; // 'outdoor' (OpenStreetMap) | 'dark' | 'satellite'

        const MAP_TILE_PROVIDERS = {
            dark: {
                url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
                attribution: '&copy; Esri World Dark Gray Base',
                subdomains: 'abc',
                maxZoom: 19
            },
            outdoor: {
                url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
                attribution: '&copy; Esri World Street Map',
                subdomains: 'abc',
                maxZoom: 19
            },
            satellite: {
                url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attribution: 'Tiles &copy; Esri - Garmin Connect Satellite Engine',
                subdomains: 'abc',
                maxZoom: 18
            }
        };

        const JAKARTA_GPS_LANDMARKS = [
            { name: "Gelora Bung Karno Senayan • Jakarta", lat: -6.2185, lon: 106.8025, tag: "GBK Loop" },
            { name: "Sudirman - Bundaran HI Track • Jakarta", lat: -6.2088, lon: 106.8228, tag: "Sudirman Corridor" },
            { name: "Monumen Nasional (Monas) • Jakarta Pusat", lat: -6.1754, lon: 106.8272, tag: "Monas Park" },
            { name: "Kuningan Rasuna Epicentrum • Jakarta", lat: -6.2198, lon: 106.8335, tag: "Epicentrum Loop" },
            { name: "Ragunan Green Trail Loop • Jakarta Selatan", lat: -6.3124, lon: 106.8202, tag: "Ragunan Trail" },
            { name: "Pantai Indah Kapuk (PIK 2) Coastal • Jakarta", lat: -6.1030, lon: 106.7400, tag: "PIK Coastal" }
        ];

        function getWorkoutRouteCoordinates(workoutIdOrData, distKm = 10, workoutType = 'run') {
            const rawGps = (workoutIdOrData && typeof workoutIdOrData === 'object') ? (workoutIdOrData.gpsRoute || workoutIdOrData.gps_route) : null;
            if (rawGps && Array.isArray(rawGps) && rawGps.length > 1) {
                return {
                    coords: rawGps,
                    locationName: workoutIdOrData.locationName || workoutIdOrData.location_name || workoutIdOrData.location || "Rute Garmin Riil"
                };
            }

            const idStr = typeof workoutIdOrData === 'string' ? workoutIdOrData : (workoutIdOrData && workoutIdOrData.id ? workoutIdOrData.id : 'w-1');
            let hash = 0;
            for (let i = 0; i < idStr.length; i++) {
                hash = (hash << 5) - hash + idStr.charCodeAt(i);
                hash |= 0;
            }
            const seedIdx = Math.abs(hash);

            const isCycling = String(workoutType).toLowerCase().includes('cycl') || String(workoutType).toLowerCase().includes('bike');
            const landmark = isCycling ? JAKARTA_GPS_LANDMARKS[5] : JAKARTA_GPS_LANDMARKS[seedIdx % (JAKARTA_GPS_LANDMARKS.length - 1)];
            
            // Prioritaskan koordinat start asli Garmin jika tercatat
            const centerLat = (workoutIdOrData && typeof workoutIdOrData === 'object' && workoutIdOrData.start_lat) ? parseFloat(workoutIdOrData.start_lat) : landmark.lat;
            const centerLon = (workoutIdOrData && typeof workoutIdOrData === 'object' && workoutIdOrData.start_lon) ? parseFloat(workoutIdOrData.start_lon) : landmark.lon;
            const locName = (workoutIdOrData && typeof workoutIdOrData === 'object' && (workoutIdOrData.location_name || workoutIdOrData.locationName)) ? (workoutIdOrData.location_name || workoutIdOrData.locationName) : landmark.name;
            const distance = Math.max(1.0, distKm || 5.0);

            // Scale realistic geographical radius (km) matching distance
            const rKm = (distance / (2 * Math.PI)) * 0.72;
            const latDeg = 1.0 / 110.574;
            const lonDeg = 1.0 / (111.320 * Math.cos(centerLat * Math.PI / 180));

            const numPoints = Math.max(50, Math.min(160, Math.round(distance * 10)));
            const coords = [];

            for (let i = 0; i < numPoints; i++) {
                const angle = (2 * Math.PI * i) / numPoints;
                const r = rKm * (1.0 + 0.32 * Math.sin(2 * angle + (seedIdx % 4)) - 0.14 * Math.cos(3 * angle));
                const dLat = r * Math.cos(angle) * latDeg;
                const dLon = r * Math.sin(angle) * 1.42 * lonDeg;
                coords.push([
                    parseFloat((centerLat + dLat).toFixed(6)),
                    parseFloat((centerLon + dLon).toFixed(6))
                ]);
            }

            // Close loop
            coords.push([coords[0][0], coords[0][1]]);

            return {
                coords: coords,
                locationName: locName || landmark.name
            };
        }

        function renderGarminMapCardSvg(w, distKm, paceFormatted, durFormatted, routeInfo) {
            const wId = String(w.id || 'w-1');
            const distNum = parseFloat(distKm) || 5.0;
            const distStr = distNum.toFixed(2);
            const paceStr = paceFormatted || '05:30 /km';
            const locationName = (routeInfo && routeInfo.locationName) ? routeInfo.locationName : 'Gelora Bung Karno (GBK) Senayan • Jakarta';
            const sport = String(w.sport || 'run').toLowerCase();

            // Schedule observer re-check after card DOM insertion
            setTimeout(() => {
                if (typeof initFeedMapObserver === 'function') initFeedMapObserver();
            }, 50);

            return `<!-- Garmin Connect Real Street Map Banner -->
            <div onclick="openActivityDetailModal('${escapeHTML(wId)}')" class="garmin-map-card relative w-full h-44 sm:h-52 rounded-xl overflow-hidden border border-border bg-[#e5e3df] cursor-pointer group hover:border-[#007cc3] transition-all duration-200 shadow-sm select-none" title="Buka Detail Aktivitas & Replay GPS">
                <!-- Real Leaflet Street Map Container -->
                <div id="feed-map-${escapeHTML(wId)}" class="garmin-feed-map-container w-full h-full z-0 pointer-events-none" data-workout-id="${escapeHTML(wId)}" data-dist="${distStr}" data-sport="${escapeHTML(sport)}"></div>

                <!-- Top Left: Venue Location Badge -->
                <div class="absolute top-2.5 left-2.5 z-[400] px-2.5 py-1 rounded-full bg-white/95 text-slate-900 shadow-sm border border-slate-300 font-mono text-[10px] flex items-center gap-1.5 font-bold max-w-[65%] truncate backdrop-blur-md">
                    <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse shrink-0"></span>
                    <span class="truncate">${escapeHTML(locationName)}</span>
                </div>

                <!-- Top Right: Weather Widget (27.2° ☀️) -->
                <div class="absolute top-2.5 right-2.5 z-[400] flex items-center gap-1.5 font-mono text-[10px]">
                    <div class="px-2 py-0.5 rounded bg-white/95 text-slate-800 shadow-sm border border-slate-300 font-bold flex items-center gap-1 backdrop-blur-md" title="Kondisi Cuaca Sesi">
                        <span>27.2°</span>
                        <svg class="w-3 h-3 text-amber-500 fill-amber-500 inline-block shrink-0" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path stroke="currentColor" stroke-width="2" stroke-linecap="round" d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32l1.41 1.41M2 12h2m16 0h2M6.34 17.66l-1.41 1.41m14.14-14.14l-1.41 1.41"/></svg>
                    </div>
                </div>

                <!-- Bottom Left: Garmin Connect Brand Header -->
                <div class="absolute bottom-2.5 left-2.5 z-[400] px-2 py-0.5 rounded bg-white/90 backdrop-blur-md border border-slate-300 text-slate-800 text-[10px] font-mono font-bold flex items-center gap-1.5 shadow-sm">
                    <svg class="w-2.5 h-2.5 fill-[#007cc3] shrink-0" viewBox="0 0 24 24"><polygon points="12 2, 22 21, 2 21"/></svg>
                    <span>GARMIN CONNECT™</span>
                </div>

                <!-- Bottom Right: Live Stats & Replay CTA -->
                <div class="absolute bottom-2.5 right-2.5 z-[400] px-2.5 py-0.5 rounded-full bg-white/90 backdrop-blur-md border border-slate-300 text-[10px] font-mono text-slate-800 flex items-center gap-1.5 shadow-sm group-hover:bg-[#007cc3] group-hover:text-white transition-colors">
                    <span class="font-bold">${distStr} km</span>
                    <span class="text-[#007cc3] group-hover:text-cyan-200">•</span>
                    <span>${escapeHTML(paceStr)}</span>
                    <span class="hidden xs:inline ml-0.5 font-bold">&rarr;</span>
                </div>
            </div>`;
        }

        function generateMiniSvgRoutePath(distKm, seedStr) {
            let hash = 0;
            const str = String(seedStr || 'w');
            for (let i = 0; i < str.length; i++) hash = (hash << 5) - hash + str.charCodeAt(i);
            const seed = Math.abs(hash);

            // Generate a natural closed SVG path for 400x112 viewbox
            const p1x = 45, p1y = 75;
            const p2x = 120 + (seed % 30), p2y = 35 + (seed % 20);
            const p3x = 240 + (seed % 40), p3y = 25 + (seed % 15);
            const p4x = 355 - (seed % 25), p4y = 48 + (seed % 20);
            const p5x = 320 - (seed % 30), p5y = 88 - (seed % 15);
            const p6x = 180 + (seed % 35), p6y = 96 - (seed % 10);
            const p7x = 53, p7y = 78;

            return `M ${p1x} ${p1y} C ${p2x} ${p2y}, ${p3x} ${p3y}, ${p4x} ${p4y} C ${p4x + 20} ${p4y + 25}, ${p5x} ${p5y}, ${p6x} ${p6y} C ${p6x - 70} ${p6y - 5}, 80 85, ${p7x} ${p7y}`;
        }

        function renderActivityDetailMap(data) {
            const mapContainer = document.getElementById('activity-leaflet-map');
            if (!mapContainer || typeof L === 'undefined') return;

            const routeInfo = (data.gpsRoute && data.gpsRoute.length > 0)
                ? { coords: data.gpsRoute, locationName: data.locationName || "Gelora Bung Karno, Senayan • Jakarta" }
                : getWorkoutRouteCoordinates(data, parseFloat(data.distance) || 10, data.sport);

            const routeCoords = routeInfo.coords;
            const locationName = routeInfo.locationName;

            // Update Map HUD Text
            const locEl = document.getElementById('detail-map-location-name');
            if (locEl) locEl.innerHTML = `<span class="w-2 h-2 rounded-full bg-emerald-400 shrink-0"></span> ${escapeHTML(locationName)}`;

            const distEl = document.getElementById('detail-map-hud-dist');
            if (distEl) distEl.textContent = data.distance || '-- km';

            const elevEl = document.getElementById('detail-map-hud-elev');
            if (elevEl) elevEl.textContent = data.elev || '+0m';

            const finishEl = document.getElementById('detail-map-hud-finish-km');
            if (finishEl) finishEl.textContent = data.distance || '-- km';

            // Lazy-init Leaflet Map instance
            if (!activityMapInstance) {
                activityMapInstance = L.map('activity-leaflet-map', {
                    zoomControl: true,
                    attributionControl: true,
                    scrollWheelZoom: true,
                    dragging: true
                });
                applyMapTileLayer(activeMapStyle);
            }

            // Remove existing layers & markers
            if (currentMapGlow) {
                activityMapInstance.removeLayer(currentMapGlow);
                currentMapGlow = null;
            }
            if (currentMapPolyline) {
                activityMapInstance.removeLayer(currentMapPolyline);
                currentMapPolyline = null;
            }
            if (currentMapMarkers && currentMapMarkers.length > 0) {
                currentMapMarkers.forEach(m => activityMapInstance.removeLayer(m));
                currentMapMarkers = [];
            }

            if (!routeCoords || routeCoords.length === 0) return;

            currentModalRouteCoords = routeCoords;
            currentModalDistanceKm = parseFloat(data.distance) || 10.0;
            resetActivityReplay();

            // Update Weather in HUD
            const weatherTempEl = document.getElementById('detail-map-weather-temp');
            if (weatherTempEl) {
                weatherTempEl.textContent = data.temperature ? `${data.temperature}°` : '27.2°';
            }

            // 1. Garmin Underglow Track Polyline
            currentMapGlow = L.polyline(routeCoords, {
                color: '#002b49',
                weight: 7,
                opacity: 0.85,
                lineCap: 'round',
                lineJoin: 'round'
            }).addTo(activityMapInstance);

            // 2. Garmin Signature Cyan/Blue Track Polyline (Matching Garmin Connect)
            currentMapPolyline = L.polyline(routeCoords, {
                color: '#007CC3',
                weight: 4.5,
                opacity: 0.95,
                lineCap: 'round',
                lineJoin: 'round'
            }).addTo(activityMapInstance);

            // 3. Garmin Start Marker: Black circle with white center (◎)
            const startPt = routeCoords[0];
            const startIcon = L.divIcon({
                className: 'garmin-map-pin-clean',
                html: '<div class="w-4 h-4 rounded-full bg-black border-2 border-white shadow-md flex items-center justify-center"><div class="w-1.5 h-1.5 rounded-full bg-white"></div></div>',
                iconSize: [16, 16],
                iconAnchor: [8, 8]
            });
            const startMarker = L.marker(startPt, { icon: startIcon, title: 'Titik Mulai (Start ◎)' })
                .addTo(activityMapInstance)
                .bindPopup(`<b>Titik Mulai (Start ◎)</b><br>0.00 km &bull; ${escapeHTML(locationName)}`);
            currentMapMarkers.push(startMarker);

            // 4. Garmin Stop Marker: Red teardrop pin with white square stop icon (⏹️)
            const finishPt = routeCoords[routeCoords.length - 1];
            const finishIcon = L.divIcon({
                className: 'garmin-map-pin-clean',
                html: '<div class="w-6 h-7 relative flex items-center justify-center"><svg class="w-6 h-7 drop-shadow-md" viewBox="0 0 24 30" fill="none"><path d="M12 0C5.373 0 0 5.373 0 12c0 9 12 18 12 18s12-9 12-18c0-6.627-5.373-12-12-12z" fill="#DC2626" stroke="#ffffff" stroke-width="1.5"/><rect x="8.5" y="8.5" width="7" height="7" rx="1" fill="#ffffff" /></svg></div>',
                iconSize: [24, 28],
                iconAnchor: [12, 28]
            });
            const finishMarker = L.marker(finishPt, { icon: finishIcon, title: `Garis Finis (Stop ⏹️)` })
                .addTo(activityMapInstance)
                .bindPopup(`<b>Garis Finis (Stop ⏹️)</b><br>${data.distance} &bull; Sesi Selesai`);
            currentMapMarkers.push(finishMarker);

            // 5. Kilometer Milestone Badges along the route
            const distNum = parseFloat(data.distance) || 5.0;
            const intervalKm = distNum > 21 ? 5 : (distNum > 8 ? 2 : 1);
            const totalPts = routeCoords.length;

            for (let km = intervalKm; km < distNum; km += intervalKm) {
                const ptIdx = Math.min(totalPts - 2, Math.round((km / distNum) * totalPts));
                const splitPt = routeCoords[ptIdx];
                if (splitPt) {
                    const splitIcon = L.divIcon({
                        className: 'garmin-map-pin garmin-pin-km',
                        html: `<span>${km}K</span>`,
                        iconSize: [26, 18],
                        iconAnchor: [13, 9]
                    });
                    const splitMarker = L.marker(splitPt, { icon: splitIcon, title: `Kilometer ${km}` })
                        .addTo(activityMapInstance)
                        .bindPopup(`<b>Kilometer ${km}</b><br>Pace: ${data.pace || '05:30 /km'}`);
                    currentMapMarkers.push(splitMarker);
                }
            }

            // Ambil rute GPS Garmin asli di latar belakang jika belum tersedia
            if ((!data.gpsRoute || data.gpsRoute.length < 2) && data.id && typeof API_BASE !== 'undefined' && !data._gpsFetching) {
                data._gpsFetching = true;
                const reqUrl = `${API_BASE}/garmin/activity-gps/${encodeURIComponent(data.id)}`;
                fetch(reqUrl)
                    .then(res => res.ok ? res.json() : null)
                    .then(json => {
                        data._gpsFetching = false;
                        if (json && json.status === 'success' && Array.isArray(json.gps_route) && json.gps_route.length > 1) {
                            data.gpsRoute = json.gps_route;
                            if (json.location_name) data.locationName = json.location_name;
                            renderActivityDetailMap(data);
                        }
                    })
                    .catch(() => { data._gpsFetching = false; });
            }

            // Adjust viewport bounds with padding
            setTimeout(() => {
                if (activityMapInstance && currentMapPolyline) {
                    activityMapInstance.invalidateSize();
                    activityMapInstance.fitBounds(currentMapPolyline.getBounds(), {
                        padding: [35, 35],
                        maxZoom: 16
                    });
                }
            }, 120);
        }

        function changeActivityMapLayer(styleName) {
            activeMapStyle = styleName;
            ['dark', 'outdoor', 'satellite'].forEach(s => {
                const btn = document.getElementById(`map-layer-${s}`);
                if (btn) {
                    if (s === styleName) {
                        btn.className = 'px-2 py-0.5 rounded border border-tertiary bg-tertiary/10 text-tertiary font-bold transition-colors';
                    } else {
                        btn.className = 'px-2 py-0.5 rounded border border-border bg-surface text-text-secondary hover:text-text-primary transition-colors';
                    }
                }
            });
            applyMapTileLayer(styleName);
            if (typeof HapticsService !== 'undefined') HapticsService.selection();
        }

        function applyMapTileLayer(styleName) {
            if (!activityMapInstance) return;
            const config = MAP_TILE_PROVIDERS[styleName] || MAP_TILE_PROVIDERS.dark;
            if (currentMapTileLayer) {
                activityMapInstance.removeLayer(currentMapTileLayer);
            }
            currentMapTileLayer = L.tileLayer(config.url, {
                attribution: config.attribution,
                subdomains: config.subdomains,
                maxZoom: config.maxZoom
            }).addTo(activityMapInstance);
        }

        function recenterActivityMap() {
            if (activityMapInstance && currentMapPolyline) {
                activityMapInstance.fitBounds(currentMapPolyline.getBounds(), {
                    padding: [35, 35],
                    maxZoom: 16
                });
                if (typeof HapticsService !== 'undefined') HapticsService.impact('LIGHT');
            }
        }

        function toggleActivityReplay() {
            if (replayAnimationTimer) {
                stopActivityReplay();
            } else {
                startActivityReplay();
            }
        }

        function startActivityReplay() {
            if (!activityMapInstance || !currentModalRouteCoords || currentModalRouteCoords.length < 2) return;
            const playBtn = document.getElementById('icon-replay-play');
            const pauseBtn = document.getElementById('icon-replay-pause');
            if (playBtn) playBtn.classList.add('hidden');
            if (pauseBtn) pauseBtn.classList.remove('hidden');

            if (replayCurrentIndex >= currentModalRouteCoords.length - 1) {
                replayCurrentIndex = 0;
            }

            if (!replayRunnerMarker) {
                const runnerIcon = L.divIcon({
                    className: 'garmin-runner-marker',
                    html: '<div class="relative flex items-center justify-center w-7 h-7"><div class="absolute w-7 h-7 rounded-full bg-cyan-400/40 animate-ping"></div><div class="relative w-5 h-5 rounded-full bg-[#007cc3] border-2 border-white shadow-md flex items-center justify-center"><svg class="w-3 h-3 text-white" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="4"/><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z"/></svg></div></div>',
                    iconSize: [24, 24],
                    iconAnchor: [12, 12]
                });
                replayRunnerMarker = L.marker(currentModalRouteCoords[replayCurrentIndex], { icon: runnerIcon, zIndexOffset: 1000 }).addTo(activityMapInstance);
            }

            replayAnimationTimer = setInterval(() => {
                if (replayCurrentIndex < currentModalRouteCoords.length - 1) {
                    replayCurrentIndex++;
                    const pt = currentModalRouteCoords[replayCurrentIndex];
                    replayRunnerMarker.setLatLng(pt);
                    const pct = Math.round((replayCurrentIndex / (currentModalRouteCoords.length - 1)) * 100);
                    const curDist = ((currentModalDistanceKm * replayCurrentIndex) / (currentModalRouteCoords.length - 1)).toFixed(2);
                    const progText = document.getElementById('replay-progress-text');
                    const progBar = document.getElementById('replay-progress-bar');
                    if (progText) progText.textContent = `${curDist} km`;
                    if (progBar) progBar.style.width = `${pct}%`;
                } else {
                    stopActivityReplay();
                }
            }, 60);
        }

        function stopActivityReplay() {
            if (replayAnimationTimer) {
                clearInterval(replayAnimationTimer);
                replayAnimationTimer = null;
            }
            const playBtn = document.getElementById('icon-replay-play');
            const pauseBtn = document.getElementById('icon-replay-pause');
            if (playBtn) playBtn.classList.remove('hidden');
            if (pauseBtn) pauseBtn.classList.add('hidden');
        }

        function resetActivityReplay() {
            stopActivityReplay();
            replayCurrentIndex = 0;
            const progText = document.getElementById('replay-progress-text');
            const progBar = document.getElementById('replay-progress-bar');
            if (progText) progText.textContent = '0.0 km';
            if (progBar) progBar.style.width = '0%';
            if (replayRunnerMarker && currentModalRouteCoords.length > 0) {
                replayRunnerMarker.setLatLng(currentModalRouteCoords[0]);
            }
        }

        function toggleActivityMapFullscreen() {
            const container = document.getElementById('detail-map-container');
            if (!container) return;
            const isFs = container.classList.toggle('garmin-map-fullscreen');
            if (isFs) {
                container.style.position = 'fixed';
                container.style.inset = '0';
                container.style.zIndex = '9999';
                container.style.width = '100vw';
                container.style.height = '100vh';
                container.style.borderRadius = '0';
            } else {
                container.style.position = '';
                container.style.inset = '';
                container.style.zIndex = '';
                container.style.width = '';
                container.style.height = '';
                container.style.borderRadius = '';
            }
            setTimeout(() => {
                if (activityMapInstance) {
                    activityMapInstance.invalidateSize();
                    if (currentMapPolyline) activityMapInstance.fitBounds(currentMapPolyline.getBounds(), { padding: [35, 35] });
                }
            }, 150);
        }

    // Attach to global window scope for inline event handlers & callers
    window.activityMapInstance = activityMapInstance;
    window.activeMapStyle = activeMapStyle;
    window.MAP_TILE_PROVIDERS = MAP_TILE_PROVIDERS;
    window.JAKARTA_GPS_LANDMARKS = JAKARTA_GPS_LANDMARKS;
    
    // ══════════════════════════════════════════════════════
    // FEED CARDS REAL STREET MAP ENGINE (INTERSECTION OBSERVER)
    // ══════════════════════════════════════════════════════
    const feedMapInstances = new Map();
    let feedMapObserver = null;

    function mountFeedCardMap(containerEl) {
        if (!containerEl || containerEl._leaflet_id || typeof L === 'undefined') return;
        const wId = containerEl.getAttribute('data-workout-id') || 'w-1';
        const dist = parseFloat(containerEl.getAttribute('data-dist')) || 5.0;
        const sport = containerEl.getAttribute('data-sport') || 'run';

        const workoutData = (typeof ACTIVITY_FIXTURES !== 'undefined' && ACTIVITY_FIXTURES[wId]) ? ACTIVITY_FIXTURES[wId] : { id: wId };
        const routeInfo = getWorkoutRouteCoordinates(workoutData, dist, sport);
        const coords = routeInfo.coords;
        if (!coords || coords.length < 2) return;

        try {
            const map = L.map(containerEl, {
                zoomControl: false,
                attributionControl: false,
                dragging: false,
                touchZoom: false,
                scrollWheelZoom: false,
                doubleClickZoom: false,
                boxZoom: false,
                keyboard: false
            });

            // Clean, authentic street map tiles (Esri World Street Map - No API key required)
            L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}', {
                maxZoom: 19,
                attribution: '&copy; Esri'
            }).addTo(map);

            // 1. Navy underglow for high contrast
            L.polyline(coords, {
                color: '#002b49',
                weight: 5.5,
                opacity: 0.85,
                lineCap: 'round',
                lineJoin: 'round'
            }).addTo(map);

            // 2. Garmin Signature Cyan/Blue polyline
            const track = L.polyline(coords, {
                color: '#007CC3',
                weight: 3.5,
                opacity: 0.95,
                lineCap: 'round',
                lineJoin: 'round'
            }).addTo(map);

            // 3. Start marker: black circle with white center (◎)
            const startIcon = L.divIcon({
                className: 'garmin-feed-start-pin',
                html: '<div class="w-4 h-4 rounded-full bg-black border-2 border-white flex items-center justify-center shadow-md"><div class="w-1.5 h-1.5 rounded-full bg-white"></div></div>',
                iconSize: [16, 16],
                iconAnchor: [8, 8]
            });
            L.marker(coords[0], { icon: startIcon }).addTo(map);

            // 4. Finish/Stop marker: red teardrop pin with white stop square (⏹)
            const finishIcon = L.divIcon({
                className: 'garmin-feed-stop-pin',
                html: '<div class="flex items-center justify-center"><svg width="18" height="22" viewBox="0 0 24 28" fill="none"><path d="M12 0C5.37 0 0 5.37 0 12c0 9 12 16 12 16s12-7 12-16c0-6.63-5.37-12-12-12z" fill="#DC2626" stroke="#FFFFFF" stroke-width="1.5"/><rect x="8.5" y="8.5" width="7" height="7" rx="1" fill="#FFFFFF"/></svg></div>',
                iconSize: [18, 22],
                iconAnchor: [9, 22]
            });
            L.marker(coords[coords.length - 1], { icon: finishIcon }).addTo(map);

            map.fitBounds(track.getBounds(), {
                padding: [22, 22]
            });

            // Ensure tile sizing is accurate once rendered in DOM
            setTimeout(() => {
                try {
                    map.invalidateSize();
                    map.fitBounds(track.getBounds(), { padding: [22, 22] });
                } catch (e) {}
            }, 60);

            feedMapInstances.set(containerEl, map);
        } catch (e) {
            console.warn('Feed map mount warning for ' + wId + ':', e);
        }
    }

    function initFeedMapObserver() {
        const containers = document.querySelectorAll('.garmin-feed-map-container');
        if (!containers || containers.length === 0) return;

        if (!('IntersectionObserver' in window)) {
            containers.forEach(el => mountFeedCardMap(el));
            return;
        }

        if (feedMapObserver) {
            feedMapObserver.disconnect();
        }

        feedMapObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    mountFeedCardMap(entry.target);
                    observer.unobserve(entry.target);
                }
            });
        }, {
            rootMargin: '250px 0px',
            threshold: 0.01
        });

        containers.forEach(el => {
            const rect = el.getBoundingClientRect();
            // If already in visible viewport, mount immediately!
            if (rect.top < window.innerHeight && rect.bottom > 0) {
                mountFeedCardMap(el);
            } else {
                feedMapObserver.observe(el);
            }
        });
    }


    window.mountFeedCardMap = mountFeedCardMap;
    window.initFeedMapObserver = initFeedMapObserver;
    window.getWorkoutRouteCoordinates = getWorkoutRouteCoordinates;
    window.renderGarminMapCardSvg = renderGarminMapCardSvg;
    window.generateMiniSvgRoutePath = generateMiniSvgRoutePath;
    window.renderActivityDetailMap = renderActivityDetailMap;
    window.changeActivityMapLayer = changeActivityMapLayer;
    window.applyMapTileLayer = applyMapTileLayer;
    window.recenterActivityMap = recenterActivityMap;
    window.toggleActivityReplay = toggleActivityReplay;
    window.startActivityReplay = startActivityReplay;
    window.stopActivityReplay = stopActivityReplay;
    window.resetActivityReplay = resetActivityReplay;
    window.toggleActivityMapFullscreen = toggleActivityMapFullscreen;

    // Auto-init feed observer on page load
    if (typeof document !== 'undefined') {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initFeedMapObserver);
        } else {
            setTimeout(initFeedMapObserver, 150);
        }
    }

})(typeof window !== 'undefined' ? window : this);
