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
                url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
                subdomains: 'abcd',
                maxZoom: 19
            },
            outdoor: {
                url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
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
            if (workoutIdOrData && typeof workoutIdOrData === 'object' && workoutIdOrData.gpsRoute && workoutIdOrData.gpsRoute.length > 0) {
                return {
                    coords: workoutIdOrData.gpsRoute,
                    locationName: workoutIdOrData.locationName || "Gelora Bung Karno Senayan • Jakarta"
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
            
            const centerLat = landmark.lat;
            const centerLon = landmark.lon;
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
                locationName: landmark.name
            };
        }

        function renderGarminMapCardSvg(w, distKm, paceFormatted, durFormatted, routeInfo) {
            const wId = String(w.id || 'w-1');
            const distNum = parseFloat(distKm) || 5.0;
            const distStr = distNum.toFixed(2);
            const paceStr = paceFormatted || '05:30 /km';
            const locationName = (routeInfo && routeInfo.locationName) ? routeInfo.locationName : 'Gelora Bung Karno (GBK) Senayan • Jakarta';
            
            let hash = 0;
            for (let i = 0; i < wId.length; i++) hash = (hash << 5) - hash + wId.charCodeAt(i);
            const seed = Math.abs(hash);

            let routePath = "";
            let startX = 82, startY = 76, finishX = 86, finishY = 80, midX = 200, midY = 32;
            let venue = locationName;
            let bgPark = "";
            let bgInner = "";
            let labelText = "";

            if (distNum < 1.0) {
                routePath = "M 120 78 C 85 78, 85 48, 120 48 L 280 48 C 315 48, 315 78, 280 78 Z";
                startX = 120; startY = 78; finishX = 126; finishY = 78; midX = 280; midY = 48;
                venue = "Stadion Madya GBK Senayan • Jakarta";
                bgPark = '<ellipse cx="200" cy="63" rx="140" ry="38" fill="#064e3b" fill-opacity="0.22" stroke="#047857" stroke-width="0.7" stroke-opacity="0.35"/>';
                bgInner = '<ellipse cx="200" cy="63" rx="90" ry="18" fill="#081422" stroke="#007cc3" stroke-width="0.8" stroke-dasharray="2,2"/>';
                labelText = '<text x="175" y="65" font-family="sans-serif" font-size="6.5" font-weight="bold" fill="#00a3e0" opacity="0.8">Trek Atletik 400m</text>';
            } else if (distNum >= 12.0 || (seed % 4 === 0)) {
                routePath = "M 82 76 C 75 46, 125 32, 200 32 C 275 32, 330 46, 325 74 C 320 90, 260 96, 200 96 C 135 96, 88 92, 82 80";
                startX = 82; startY = 76; finishX = 86; finishY = 80; midX = 200; midY = 32;
                venue = "Gelora Bung Karno (GBK) Senayan • Jakarta";
                bgPark = '<ellipse cx="200" cy="64" rx="145" ry="42" fill="#064e3b" fill-opacity="0.20" stroke="#047857" stroke-width="0.8" stroke-opacity="0.3"/>';
                bgInner = '<ellipse cx="200" cy="64" rx="42" ry="20" fill="#071322" stroke="#007cc3" stroke-width="1" stroke-opacity="0.5" stroke-dasharray="3,2"/>';
                labelText = '<text x="170" y="66" font-family="sans-serif" font-size="6.5" font-weight="bold" fill="#10b981" opacity="0.8">Stadion Utama GBK</text>';
            } else if (seed % 4 === 1) {
                routePath = "M 95 86 L 95 36 Q 95 32 99 32 L 305 32 Q 310 32 310 36 L 310 86 Q 310 90 305 90 L 102 90";
                startX = 95; startY = 86; finishX = 102; finishY = 90; midX = 202; midY = 32;
                venue = "Monumen Nasional (Monas) • Jakarta Pusat";
                bgPark = '<rect x="85" y="24" width="235" height="74" rx="6" fill="#064e3b" fill-opacity="0.22" stroke="#047857" stroke-width="0.7" stroke-opacity="0.35"/>';
                bgInner = '<rect x="180" y="48" width="45" height="26" rx="3" fill="#0f291e" stroke="#10b981" stroke-width="0.5" stroke-opacity="0.4"/>';
                labelText = '<text x="185" y="63" font-family="sans-serif" font-size="6.5" font-weight="bold" fill="#10b981" opacity="0.8">Taman Monas</text>';
            } else if (seed % 4 === 2) {
                routePath = "M 55 90 C 105 84, 140 70, 180 58 C 215 48, 255 36, 310 30 C 332 28, 342 38, 332 44 C 295 56, 235 68, 180 76 C 130 82, 90 88, 62 90";
                startX = 55; startY = 90; finishX = 62; finishY = 90; midX = 330; midY = 36;
                venue = "Sudirman - Bundaran HI Track • Jakarta";
                bgPark = '<path d="M 160 52 C 180 40, 200 40, 220 52 C 200 64, 180 64, 160 52 Z" fill="#064e3b" fill-opacity="0.25" stroke="#047857" stroke-width="0.5"/>';
                bgInner = '<circle cx="325" cy="36" r="14" fill="#0369a1" fill-opacity="0.2" stroke="#0284c7" stroke-width="0.8" stroke-dasharray="2,2"/>';
                labelText = '<text x="195" y="62" font-family="sans-serif" font-size="6.5" font-weight="bold" fill="#64748b" opacity="0.8">Jl. Jend. Sudirman</text>';
            } else {
                routePath = "M 70 82 C 90 42, 145 34, 205 44 C 265 54, 315 36, 340 54 C 352 68, 305 86, 240 82 C 175 78, 110 86, 76 84";
                startX = 70; startY = 82; finishX = 76; finishY = 84; midX = 205; midY = 44;
                venue = "Kuningan Rasuna Epicentrum • Jakarta";
                bgPark = '<path d="M 60 50 Q 200 55 350 48" stroke="#0284c7" stroke-width="3" stroke-opacity="0.25" fill="none"/>';
                bgInner = '';
                labelText = '<text x="160" y="44" font-family="sans-serif" font-size="6.5" font-weight="bold" fill="#0284c7" opacity="0.8">Kanal Epicentrum</text>';
            }

            return `<!-- Garmin Connect GPS Route Map Banner -->
            <div onclick="openActivityDetailModal('${escapeHTML(wId)}')" class="garmin-map-card relative w-full h-32 rounded-xl overflow-hidden border border-[#007cc3]/40 bg-[#060c18] cursor-pointer group hover:border-[#00a3e0] transition-all duration-200 shadow-md select-none" title="Buka Peta GPS Telemetri Garmin Connect">
                <!-- Garmin Real Street Map Canvas -->
                <svg class="w-full h-full relative z-10" viewBox="0 0 400 128" preserveAspectRatio="none">
                    <defs>
                        <linearGradient id="garmin-cyan-glow-${escapeHTML(wId)}" x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" stop-color="#00A3E0" />
                            <stop offset="50%" stop-color="#00E5FF" />
                            <stop offset="100%" stop-color="#007CC3" />
                        </linearGradient>
                        <pattern id="garmin-grid-${escapeHTML(wId)}" width="28" height="28" patternUnits="userSpaceOnUse">
                            <path d="M 28 0 L 0 0 0 28" fill="none" stroke="#1e293b" stroke-width="0.5" stroke-opacity="0.45"/>
                            <circle cx="28" cy="0" r="0.6" fill="#334155" opacity="0.6" />
                        </pattern>
                        <filter id="garmin-track-glow-${escapeHTML(wId)}" x="-10%" y="-10%" width="120%" height="120%">
                            <feDropShadow dx="0" dy="0" stdDeviation="2.5" flood-color="#00A3E0" flood-opacity="0.8"/>
                        </filter>
                    </defs>

                    <!-- Base Grid & Street Map Background -->
                    <rect width="400" height="128" fill="#060c18" />
                    <rect width="400" height="128" fill="url(#garmin-grid-${escapeHTML(wId)})" opacity="0.75" />

                    <!-- City Street Network (Arterial & Secondary Roads) -->
                    <g stroke="#1a273a" stroke-linecap="round" opacity="0.7">
                        <path d="M 0 40 Q 200 35 400 45" stroke-width="2.5" fill="none" />
                        <path d="M 0 88 Q 200 92 400 82" stroke-width="2.5" fill="none" />
                        <path d="M 120 0 L 120 128" stroke-width="1.2" stroke-dasharray="4,4" />
                        <path d="M 280 0 L 280 128" stroke-width="1.2" stroke-dasharray="4,4" />
                        <path d="M 40 10 L 40 118" stroke-width="0.8" opacity="0.4" />
                        <path d="M 200 10 L 200 118" stroke-width="0.8" opacity="0.4" />
                        <path d="M 360 10 L 360 118" stroke-width="0.8" opacity="0.4" />
                    </g>

                    <!-- Park / Water Venue Landmark Polygons -->
                    ${bgPark}
                    ${bgInner}
                    ${labelText}

                    <!-- Garmin GPS Telemetry Crosshairs & Coordinate Marks -->
                    <g stroke="#334155" stroke-width="0.8" opacity="0.7">
                        <path d="M 18 14 L 18 22 M 14 18 L 22 18" />
                        <path d="M 382 14 L 382 22 M 378 18 L 386 18" />
                        <path d="M 18 106 L 18 114 M 14 110 L 22 110" />
                        <path d="M 382 106 L 382 114 M 378 110 L 386 110" />
                    </g>
                    <text x="35" y="21" font-family="monospace" font-size="7" fill="#475569" opacity="0.8">106°48'E • -6°13'S</text>
                    <text x="382" y="32" font-family="monospace" font-size="7" fill="#00a3e0" opacity="0.8" text-anchor="end">N ↑</text>

                    <!-- 1. Deep Navy Track Underglow -->
                    <path d="${routePath}" fill="none" stroke="#001a33" stroke-width="7" stroke-linecap="round" stroke-linejoin="round" opacity="0.9" />

                    <!-- 2. Garmin Signature Cyan GPS Track -->
                    <path d="${routePath}" fill="none" stroke="url(#garmin-cyan-glow-${escapeHTML(wId)})" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" filter="url(#garmin-track-glow-${escapeHTML(wId)})" />

                    <!-- 3. Mid-route Checkpoint Marker -->
                    <circle cx="${midX}" cy="${midY}" r="2" fill="#007CC3" stroke="#ffffff" stroke-width="1" />

                    <!-- 4. Garmin Start Marker (◎ - Black ring with white center) -->
                    <circle cx="${startX}" cy="${startY}" r="5.5" fill="#000000" stroke="#ffffff" stroke-width="1.8" />
                    <circle cx="${startX}" cy="${startY}" r="1.8" fill="#ffffff" />

                    <!-- 5. Garmin Stop Marker (⏹️ - Red pin with white stop square) -->
                    <g transform="translate(${finishX - 7}, ${finishY - 13})">
                        <path d="M7 0C3.13 0 0 3.13 0 7c0 5.25 7 10.5 7 10.5s7-5.25 7-10.5c0-3.87-3.13-7-7-7z" fill="#DC2626" stroke="#ffffff" stroke-width="1"/>
                        <rect x="4.8" y="4.8" width="4.4" height="4.4" rx="0.5" fill="#ffffff" />
                    </g>
                </svg>

                <!-- Top Left: Garmin Connect Brand Header -->
                <div class="absolute top-2.5 left-2.5 z-20 px-2 py-0.5 rounded bg-[#00172e]/90 backdrop-blur-md border border-[#007cc3]/60 text-[#00a3e0] text-[10px] font-mono font-bold flex items-center gap-1.5 shadow-sm">
                    <svg class="w-2.5 h-2.5 fill-[#00a3e0] shrink-0" viewBox="0 0 24 24"><polygon points="12 2, 22 21, 2 21"/></svg>
                    <span>GARMIN CONNECT™</span>
                </div>

                <!-- Top Right: Weather Widget (27.2° ☀️) & 3D GPS HUD -->
                <div class="absolute top-2.5 right-2.5 z-20 flex items-center gap-1.5 font-mono text-[10px]">
                    <div class="px-2 py-0.5 rounded bg-white/95 text-slate-800 shadow-sm border border-slate-300 font-bold flex items-center gap-1" title="Kondisi Cuaca Sesi">
                        <span>27.2°</span>
                        <svg class="w-3 h-3 text-amber-500 fill-amber-500 inline-block shrink-0" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path stroke="currentColor" stroke-width="2" stroke-linecap="round" d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32l1.41 1.41M2 12h2m16 0h2M6.34 17.66l-1.41 1.41m14.14-14.14l-1.41 1.41"/></svg>
                    </div>
                    <div class="px-2 py-0.5 rounded bg-[#00172e]/90 backdrop-blur-md border border-[#007cc3]/60 text-cyan-300 flex items-center gap-1 group-hover:text-white transition-all shadow-sm">
                        <span>GPS 3D</span>
                        <svg class="w-2.5 h-2.5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
                    </div>
                </div>

                <!-- Bottom Left: Venue Location Badge -->
                <div class="absolute bottom-2.5 left-2.5 z-20 px-2.5 py-1 rounded-full bg-black/85 backdrop-blur-md text-[10px] font-mono text-white flex items-center gap-1.5 border border-[#007cc3]/40 shadow-sm max-w-[65%] sm:max-w-none truncate">
                    <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse shrink-0"></span>
                    <span class="font-bold truncate">${escapeHTML(venue)}</span>
                </div>

                <!-- Bottom Right: Live Stats Chip -->
                <div class="absolute bottom-2.5 right-2.5 z-20 px-2 py-0.5 rounded bg-black/85 backdrop-blur-md border border-white/10 text-[10px] font-mono text-slate-300 hidden xs:flex items-center gap-1.5 shadow-sm">
                    <span class="text-white font-bold">${distStr} km</span>
                    <span class="text-cyan-400">•</span>
                    <span>${escapeHTML(paceStr)}</span>
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
})(typeof window !== 'undefined' ? window : this);
