/**
 * Goalie Interactive GPX Elevation Scrubber Module
 * Synchronizes the course elevation profile with Leaflet map coordinates in real-time.
 */

(function (window) {
    'use strict';

    class CourseElevationScrubber {
        constructor() {
            this.map = null;
            this.marker = null;
            this.coordinates = []; // Array of [lat, lng, elevation_m, distance_km]
            this.totalDistanceKm = 42.195;
            this.isInitialized = false;
        }

        init(leafletMap, courseCoordinates, totalDistanceKm) {
            this.map = leafletMap;
            this.coordinates = courseCoordinates || [];
            this.totalDistanceKm = totalDistanceKm || 42.195;
            this.isInitialized = true;
            this._createPulsingMarker();
        }

        _createPulsingMarker() {
            if (!this.map || typeof L === 'undefined') return;

            const icon = L.divIcon({
                className: 'gpx-scrubber-icon',
                html: `
                    <div style="position:relative; width:20px; height:20px;">
                        <span style="position:absolute; inset:0; border-radius:9999px; background:#fc4c02; opacity:0.4; animation:ping 1.5s cubic-bezier(0,0,0.2,1) infinite;"></span>
                        <span style="position:absolute; inset:3px; border-radius:9999px; background:#fc4c02; border:2px solid #ffffff; box-shadow:0 2px 4px rgba(0,0,0,0.3);"></span>
                    </div>
                `,
                iconSize: [20, 20],
                iconAnchor: [10, 10]
            });

            if (this.coordinates.length > 0) {
                const first = this.coordinates[0];
                this.marker = L.marker([first[0], first[1]], { icon: icon, zIndexOffset: 1000 }).addTo(this.map);
                this.marker.setOpacity(0);
            }
        }

        scrubToDistance(km) {
            if (!this.map || !this.marker || this.coordinates.length === 0) return;

            const clampedKm = Math.max(0, Math.min(this.totalDistanceKm, km));
            const progress = clampedKm / this.totalDistanceKm;
            const index = Math.min(
                this.coordinates.length - 1,
                Math.max(0, Math.floor(progress * (this.coordinates.length - 1)))
            );

            const pt = this.coordinates[index];
            if (!pt) return;

            const lat = pt[0];
            const lng = pt[1];
            const elevation = pt[2] || 15;

            this.marker.setLatLng([lat, lng]);
            this.marker.setOpacity(1);

            const popupContent = `
                <div style="font-family:monospace; font-size:11px; padding:2px 4px; line-height:1.3;">
                    <strong style="color:#fc4c02; font-weight:bold;">${clampedKm.toFixed(1)} km</strong><br/>
                    <span style="color:#666;">Elevasi: ${Math.round(elevation)} m</span>
                </div>
            `;
            this.marker.bindTooltip(popupContent, {
                permanent: false,
                direction: 'top',
                offset: [0, -10],
                className: 'scrubber-tooltip'
            }).openTooltip();
        }

        hideScrubber() {
            if (this.marker) {
                this.marker.setOpacity(0);
                this.marker.closeTooltip();
            }
        }
    }

    window.GoalieElevationScrubber = new CourseElevationScrubber();

})(typeof window !== 'undefined' ? window : this);
