/**
 * Garmin Sync Manager (Goalie V2)
 * Modul orkestrasi sinkronisasi Garmin Connect Near-Real-Time & Auto-GPS Pipeline.
 * 
 * Fitur:
 * 1. Focus & Tab-Visibility Auto Check (otomatis mendeteksi aktivitas baru saat membuka aplikasi).
 * 2. Background Auto-Poll Scheduler (pemeriksaan berkala aktivitas Garmin).
 * 3. Lazy GPS Polyline Preloader (mengunduh rute jalanan riil secara asinkron).
 * 4. UI Telemetry Status Pill & Toast Notifikasi.
 */

(function (root, factory) {
    if (typeof define === 'function' && define.amd) {
        define([], factory);
    } else if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else {
        root.GarminSyncManager = factory();
    }
}(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    const CONFIG_KEYS = {
        ENABLED: 'goalie_garmin_autosync_enabled',
        INTERVAL_MINUTES: 'goalie_garmin_autosync_interval',
        LAST_SYNC_TS: 'goalie_garmin_last_sync_timestamp'
    };

    let _pollTimer = null;
    let _isChecking = false;
    let _lastSyncTime = null;
    let _isConnected = false;

    // Inisialisasi state dari localStorage
    try {
        const storedTs = localStorage.getItem(CONFIG_KEYS.LAST_SYNC_TS);
        if (storedTs) _lastSyncTime = new Date(storedTs);
    } catch (e) {}

    function isAutoSyncEnabled() {
        try {
            const val = localStorage.getItem(CONFIG_KEYS.ENABLED);
            return val === null ? true : val === 'true'; // Default aktif
        } catch (e) {
            return true;
        }
    }

    function setAutoSyncEnabled(enabled) {
        try {
            localStorage.setItem(CONFIG_KEYS.ENABLED, String(Boolean(enabled)));
            if (enabled) {
                startScheduler();
            } else {
                stopScheduler();
            }
            updateStatusUI();
        } catch (e) {}
    }

    function getPollIntervalMinutes() {
        try {
            const val = parseInt(localStorage.getItem(CONFIG_KEYS.INTERVAL_MINUTES), 10);
            return (val && val >= 2 && val <= 60) ? val : 5; // Default 5 menit
        } catch (e) {
            return 5;
        }
    }

    function setPollIntervalMinutes(minutes) {
        try {
            const m = Math.max(2, Math.min(60, parseInt(minutes, 10) || 5));
            localStorage.setItem(CONFIG_KEYS.INTERVAL_MINUTES, String(m));
            if (isAutoSyncEnabled()) {
                startScheduler();
            }
            updateStatusUI();
        } catch (e) {}
    }

    function getAuthHeaders() {
        const headers = { 'Content-Type': 'application/json' };
        try {
            const token = localStorage.getItem('goalie_token') || localStorage.getItem('access_token');
            if (token) headers['Authorization'] = `Bearer ${token}`;
        } catch (e) {}
        return headers;
    }

    function getApiBase() {
        if (typeof window.API_BASE !== 'undefined') return window.API_BASE;
        return (typeof window.location !== 'undefined' && window.location.pathname.startsWith('/golie'))
            ? `${window.location.origin}/golie/api/v1`
            : `${window.location.origin}/api/v1`;
    }

    /**
     * Memeriksa aktivitas baru dari Garmin Connect via endpoint auto-sync-check
     */
    async function checkNewActivities(isManual = false) {
        if (_isChecking) return;
        _isChecking = true;
        updateStatusUI();

        try {
            const apiBase = getApiBase();
            const res = await fetch(`${apiBase}/garmin/auto-sync-check`, {
                method: 'POST',
                headers: getAuthHeaders()
            });

            if (!res.ok) {
                if (res.status === 401 || res.status === 403) {
                    _isConnected = false;
                }
                _isChecking = false;
                updateStatusUI();
                return;
            }

            const data = await res.json();
            _isConnected = Boolean(data.connected);

            if (data.connected && data.has_new && data.new_count > 0) {
                _lastSyncTime = new Date();
                try {
                    localStorage.setItem(CONFIG_KEYS.LAST_SYNC_TS, _lastSyncTime.toISOString());
                } catch (e) {}

                // Tampilkan notifikasi
                if (typeof toast !== 'undefined' && typeof toast.success === 'function') {
                    toast.success(
                        'Garmin Live Sync',
                        `${data.new_count} aktivitas lari baru berhasil disinkronkan dari Garmin Connect.`
                    );
                }

                // Segarkan data dashboard dan peta
                if (typeof window.syncCockpitWithBackend === 'function') {
                    window.syncCockpitWithBackend();
                }
                if (typeof window.syncTelemetrySuite === 'function') {
                    window.syncTelemetrySuite();
                }

                // Dispatch event global
                if (typeof window.dispatchEvent === 'function') {
                    window.dispatchEvent(new CustomEvent('goalie:garmin_synced', { detail: data }));
                }
            } else if (isManual) {
                _lastSyncTime = new Date();
                try {
                    localStorage.setItem(CONFIG_KEYS.LAST_SYNC_TS, _lastSyncTime.toISOString());
                } catch (e) {}
                if (typeof toast !== 'undefined' && typeof toast.info === 'function') {
                    toast.info(
                        'Garmin Up to Date',
                        data.message || 'Semua aktivitas Garmin sudah tersinkronisasi terbaru.'
                    );
                }
            }
        } catch (err) {
            console.debug('[GarminSyncManager] Auto-sync check note:', err.message);
        } finally {
            _isChecking = false;
            updateStatusUI();
        }
    }

    /**
     * Memulai background scheduler
     */
    function startScheduler() {
        stopScheduler();
        if (!isAutoSyncEnabled()) return;

        const intervalMs = getPollIntervalMinutes() * 60 * 1000;
        _pollTimer = setInterval(() => {
            // Hanya jalankan jika tab sedang aktif dan dokumen terlihat
            if (typeof document !== 'undefined' && document.visibilityState === 'visible') {
                checkNewActivities(false);
            }
        }, intervalMs);
    }

    function stopScheduler() {
        if (_pollTimer) {
            clearInterval(_pollTimer);
            _pollTimer = null;
        }
    }

    /**
     * Format waktu relatif ringkas (misal: "Baru saja", "3m lalu")
     */
    function formatRelativeTime(dateObj) {
        if (!dateObj) return 'Belum pernah';
        const diffSec = Math.floor((new Date() - new Date(dateObj)) / 1000);
        if (diffSec < 60) return 'Baru saja';
        if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m lalu`;
        if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}j lalu`;
        return `${Math.floor(diffSec / 86400)}h lalu`;
    }

    /**
     * Memperbarui visual status bar / pill di antarmuka pengguna
     */
    function updateStatusUI() {
        const pills = document.querySelectorAll('.garmin-sync-status-pill');
        if (!pills || pills.length === 0) return;

        const enabled = isAutoSyncEnabled();
        const timeStr = formatRelativeTime(_lastSyncTime);

        pills.forEach(pill => {
            if (_isChecking) {
                pill.innerHTML = `
                    <span class="w-2 h-2 rounded-full bg-cyan-400 animate-ping"></span>
                    <span class="text-[11px] font-mono text-cyan-300 font-bold">Sinkronisasi Garmin...</span>
                `;
            } else if (enabled) {
                pill.innerHTML = `
                    <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                    <span class="text-[11px] font-mono text-text-secondary">Garmin Auto-Sync:</span>
                    <strong class="text-[11px] font-mono text-emerald-500 font-bold">${timeStr}</strong>
                    <button type="button" onclick="GarminSyncManager.checkNow(true)" class="ml-1 p-0.5 rounded hover:bg-surface-subtle text-text-secondary hover:text-tertiary transition-colors" title="Cek Aktivitas Garmin Baru Sekarang">
                        <svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
                    </button>
                `;
            } else {
                pill.innerHTML = `
                    <span class="w-1.5 h-1.5 rounded-full bg-slate-400"></span>
                    <span class="text-[11px] font-mono text-text-secondary">Garmin Sync: Manual</span>
                    <button type="button" onclick="GarminSyncManager.checkNow(true)" class="ml-1 px-1.5 py-0.2 rounded bg-surface border border-border text-[10px] font-mono hover:text-tertiary">
                        Sync Sekarang
                    </button>
                `;
            }
        });
    }

    /**
     * Inisialisasi event listener jendela (Focus & Visibility)
     */
    function init() {
        if (typeof document === 'undefined') return;

        // Auto-check saat tab browser kembali aktif
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible' && isAutoSyncEnabled()) {
                const now = new Date();
                const diffMin = _lastSyncTime ? (now - _lastSyncTime) / 60000 : 999;
                // Jika sudah lebih dari 2 menit sejak sinkronisasi terakhir
                if (diffMin >= 2) {
                    checkNewActivities(false);
                } else {
                    updateStatusUI();
                }
            }
        });

        // Window focus event
        window.addEventListener('focus', () => {
            if (isAutoSyncEnabled()) {
                const now = new Date();
                const diffMin = _lastSyncTime ? (now - _lastSyncTime) / 60000 : 999;
                if (diffMin >= 3) {
                    checkNewActivities(false);
                }
            }
        });

        startScheduler();
        setTimeout(updateStatusUI, 300);
    }

    // Auto-init saat dokumen siap
    if (typeof document !== 'undefined') {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
        } else {
            setTimeout(init, 200);
        }
    }

    return {
        init: init,
        checkNow: checkNewActivities,
        isAutoSyncEnabled: isAutoSyncEnabled,
        setAutoSyncEnabled: setAutoSyncEnabled,
        getPollIntervalMinutes: getPollIntervalMinutes,
        setPollIntervalMinutes: setPollIntervalMinutes,
        updateStatusUI: updateStatusUI,
        formatRelativeTime: formatRelativeTime,
        getLastSyncTime: () => _lastSyncTime
    };
}));
