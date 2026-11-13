/**
 * Goalie SaaS Settings Controller Module
 * Handles category switching, search filtering, Karvonen calculations,
 * credential management, and data portability.
 */

(function (window) {
    'use strict';

    function switchSettingsCategory(categoryId) {
        const categories = ['profile', 'preferences', 'appearance', 'notifications', 'security', 'integrations', 'data', 'billing', 'support', 'about', 'ai-coach'];
        categories.forEach(cat => {
            const pane = document.getElementById(`settings-pane-${cat}`);
            const btn = document.getElementById(`settings-cat-btn-${cat}`);
            if (pane) pane.classList.toggle('hidden', cat !== categoryId);
            if (btn) {
                if (cat === categoryId) {
                    btn.className = 'settings-cat-btn active w-full flex items-center justify-between p-2.5 rounded-xl bg-tertiary/10 border border-tertiary/20 text-left transition-all group';
                } else {
                    btn.className = 'settings-cat-btn w-full flex items-center justify-between p-2.5 rounded-xl hover:bg-surface-subtle border border-transparent text-left transition-all group';
                }
            }
        });

        if (window.innerWidth < 768) {
            const paneEl = document.getElementById(`settings-pane-${categoryId}`);
            if (paneEl) {
                paneEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }
    }

    function filterSettingsSections(query) {
        const q = (query || '').toLowerCase().trim();
        const panes = document.querySelectorAll('.settings-pane');
        if (!q) {
            const activeBtn = document.querySelector('.settings-cat-btn.active');
            const activeCat = activeBtn ? activeBtn.dataset.cat : 'profile';
            switchSettingsCategory(activeCat);
            return;
        }
        panes.forEach(pane => {
            const text = pane.textContent.toLowerCase();
            pane.classList.toggle('hidden', !text.includes(q));
        });
    }

    function updateKarvonenCalculation() {
        const maxHr = parseInt(document.getElementById('settings-max-hr')?.value, 10) || 192;
        const rhr = parseInt(document.getElementById('settings-resting-hr')?.value, 10) || 48;
        
        let zones;
        if (window.GoalieSportsMath && typeof window.GoalieSportsMath.calculateKarvonenZones === 'function') {
            zones = window.GoalieSportsMath.calculateKarvonenZones(rhr, maxHr);
        } else {
            const hrr = Math.max(0, maxHr - rhr);
            const z1 = Math.round(rhr + (hrr * 0.60));
            const z2 = Math.round(rhr + (hrr * 0.70));
            const z3 = Math.round(rhr + (hrr * 0.80));
            const z4 = Math.round(rhr + (hrr * 0.90));
            zones = {
                hrr,
                zone1: { max: z1 },
                zone2: { min: z1, max: z2 },
                zone3: { min: z2, max: z3 },
                zone4: { min: z3, max: z4 },
                zone5: { min: z4 }
            };
        }

        const hrrEl = document.getElementById('settings-hrr-display');
        const z1El = document.getElementById('settings-z1-range');
        const z2El = document.getElementById('settings-z2-range');
        const z3El = document.getElementById('settings-z3-range');
        const z4El = document.getElementById('settings-z4-range');
        const z5El = document.getElementById('settings-z5-range');

        if (hrrEl) hrrEl.textContent = `${zones.hrr} bpm`;
        if (z1El) z1El.textContent = `< ${zones.zone1.max} bpm`;
        if (z2El) z2El.textContent = `${zones.zone2.min} - ${zones.zone2.max} bpm`;
        if (z3El) z3El.textContent = `${zones.zone3.min} - ${zones.zone3.max} bpm`;
        if (z4El) z4El.textContent = `${zones.zone4.min} - ${zones.zone4.max} bpm`;
        if (z5El) z5El.textContent = `> ${zones.zone5.min} bpm`;
    }

    function markSettingsUnsaved() {
        const statusBadge = document.getElementById('settings-save-status');
        if (statusBadge) {
            statusBadge.textContent = 'PERUBAHAN BELUM DISIMPAN';
            statusBadge.className = 'flat-badge border-flat-orange text-flat-orange font-mono';
        }
    }

    function handleAutomationToggle(key, isChecked) {
        localStorage.setItem(`goalie_auto_${key}`, isChecked ? '1' : '0');
        markSettingsUnsaved();
        const label = key === 'preload_gps' ? 'Pre-load GPX & Elevasi' : 'Penyesuaian Cuaca & Suhu';
        if (window.toast) {
            window.toast.info('Preferensi Otomasi Disimpan', `${label} ${isChecked ? 'diaktifkan' : 'dinonaktifkan'}.`);
        }
    }

    async function handlePasswordChangeInSettings() {
        const curEl = document.getElementById('settings-pwd-current');
        const newEl = document.getElementById('settings-pwd-new');
        const confEl = document.getElementById('settings-pwd-confirm');
        const btn = document.getElementById('btn-change-pwd-settings');

        const currentPassword = curEl ? curEl.value.trim() : '';
        const newPassword = newEl ? newEl.value.trim() : '';
        const confirmPassword = confEl ? confEl.value.trim() : '';

        if (!currentPassword) {
            if (window.toast) window.toast.warning('Kata Sandi Diperlukan', 'Masukkan kata sandi akun Anda saat ini.');
            if (curEl) curEl.focus();
            return;
        }
        if (!newPassword || newPassword.length < 6) {
            if (window.toast) window.toast.warning('Kata Sandi Terlalu Pendek', 'Kata sandi baru minimal harus 6 karakter.');
            if (newEl) newEl.focus();
            return;
        }
        if (newPassword !== confirmPassword) {
            if (window.toast) window.toast.error('Kata Sandi Tidak Cocok', 'Konfirmasi kata sandi baru tidak sama.');
            if (confEl) confEl.focus();
            return;
        }
        if (newPassword === currentPassword) {
            if (window.toast) window.toast.warning('Kata Sandi Sama', 'Kata sandi baru harus berbeda dari kata sandi lama.');
            if (newEl) newEl.focus();
            return;
        }

        if (btn) {
            btn.disabled = true;
            btn.textContent = 'MEMPERBARUI...';
        }

        try {
            const apiBase = window.API_BASE || '/golie/api/v1';
            const headers = (typeof window.getAuthHeaders === 'function') ? window.getAuthHeaders() : { 'Content-Type': 'application/json' };
            const res = await fetch(`${apiBase}/auth/change-password`, {
                method: 'POST',
                headers: {
                    ...headers,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    current_password: currentPassword,
                    new_password: newPassword
                })
            });

            const data = await res.json().catch(() => ({}));

            if (!res.ok) {
                const msg = data.detail || 'Gagal mengubah kata sandi. Periksa kata sandi saat ini.';
                if (window.toast) window.toast.error('Gagal Memperbarui', msg);
                return;
            }

            if (curEl) curEl.value = '';
            if (newEl) newEl.value = '';
            if (confEl) confEl.value = '';

            if (window.toast) window.toast.success('Kata Sandi Diperbarui', 'Kata sandi akun Anda berhasil diperbarui dengan hashing aman PBKDF2.');
        } catch (err) {
            console.error('[Goalie] Change password error:', err);
            if (window.toast) window.toast.error('Koneksi Gagal', 'Gagal menghubungi server untuk memperbarui kata sandi.');
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.textContent = 'Simpan Kata Sandi Baru';
            }
        }
    }

    function handleAthleteDataImport(event) {
        const file = event.target.files?.[0];
        if (!file) return;

        const filenameEl = document.getElementById('settings-import-filename');
        if (filenameEl) filenameEl.textContent = file.name;

        const reader = new FileReader();
        reader.onload = function(e) {
            try {
                const data = JSON.parse(e.target.result);
                if (!data || typeof data !== 'object') {
                    throw new Error('Format file tidak valid');
                }

                if (data.cockpit_telemetry && window.cockpitData) {
                    window.cockpitData = {
                        ...window.cockpitData,
                        ...data.cockpit_telemetry
                    };
                }

                if (data.athlete && window.appState) {
                    if (data.athlete.email && !window.appState.userEmail) {
                        window.appState.userEmail = data.athlete.email;
                    }
                    if (typeof data.athlete.is_pro === 'boolean') {
                        window.appState.isPro = data.athlete.is_pro;
                        localStorage.setItem('user_is_pro_subscription', data.athlete.is_pro ? 'true' : 'false');
                    }
                    if (data.athlete.selected_coach_tier && typeof window.selectCoachTier === 'function') {
                        window.selectCoachTier(data.athlete.selected_coach_tier, false);
                    }
                }

                if (typeof window.updateCockpitVisuals === 'function') {
                    window.updateCockpitVisuals();
                }

                if (window.toast) window.toast.success('Data Berhasil Diimpor', `File cadangan ${file.name} berhasil dipulihkan ke sesi atlet.`);
            } catch (err) {
                console.error('[Goalie] Import data error:', err);
                if (window.toast) window.toast.error('Format Tidak Cocok', 'File JSON tidak berisi struktur telemetri Goalie yang valid.');
            } finally {
                event.target.value = '';
            }
        };
        reader.onerror = function() {
            if (window.toast) window.toast.error('Gagal Membaca File', 'Terjadi kesalahan saat membaca file dari penyimpanan perangkat.');
            event.target.value = '';
        };
        reader.readAsText(file);
    }

    // Export to global window scope for inline onclick handlers
    window.switchSettingsCategory = switchSettingsCategory;
    window.filterSettingsSections = filterSettingsSections;
    window.updateKarvonenCalculation = updateKarvonenCalculation;
    window.markSettingsUnsaved = markSettingsUnsaved;
    window.handleAutomationToggle = handleAutomationToggle;
    window.handlePasswordChangeInSettings = handlePasswordChangeInSettings;
    window.handleAthleteDataImport = handleAthleteDataImport;

})(typeof window !== 'undefined' ? window : this);
