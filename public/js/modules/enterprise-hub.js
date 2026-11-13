/**
 * Goalie Enterprise Operational Suite Module
 * Manages Notifications, User Management, Analytics Reports, Billing,
 * Help & Support, and System Status Pages.
 */

(function (window) {
    'use strict';

    const GoalieEnterprise = {
        state: {
            unreadNotifications: 2,
            notifications: [],
            teamMembers: [],
            invoices: []
        },

        // ══════════════════════════════════════════════════════════
        // 6. NOTIFICATION CENTER & ALERTS
        // ══════════════════════════════════════════════════════════
        toggleNotificationCenter: function () {
            const panel = document.getElementById('notification-center-drawer');
            if (!panel) return;
            const isHidden = panel.classList.contains('hidden');
            if (isHidden) {
                panel.classList.remove('hidden');
                GoalieEnterprise.fetchNotifications();
            } else {
                panel.classList.add('hidden');
            }
            if (window.GoalieMobile) window.GoalieMobile.triggerHaptic('selection');
        },

        closeNotificationCenter: function () {
            const panel = document.getElementById('notification-center-drawer');
            if (panel) panel.classList.add('hidden');
        },

        fetchNotifications: async function () {
            try {
                const apiBase = window.API_BASE || '/golie/api/v1';
                const headers = (typeof window.getAuthHeaders === 'function') ? window.getAuthHeaders() : {};
                const res = await fetch(`${apiBase}/notifications`, { headers });
                if (!res.ok) return;
                const data = await res.json();
                GoalieEnterprise.state.notifications = data.notifications || [];
                GoalieEnterprise.state.unreadNotifications = data.unread_count || 0;
                GoalieEnterprise.renderNotificationFeed('all');
                GoalieEnterprise.updateNotificationBadge();
            } catch (err) {
                console.warn('[Goalie] Notifications fetch warning:', err);
            }
        },

        filterNotifications: function (category) {
            GoalieEnterprise.renderNotificationFeed(category);
            const tabs = ['all', 'alert', 'reminder'];
            tabs.forEach(t => {
                const btn = document.getElementById(`notif-tab-${t}`);
                if (btn) {
                    if (t === category) {
                        btn.className = 'px-2.5 py-1 text-[11px] font-bold rounded-md bg-tertiary text-white';
                    } else {
                        btn.className = 'px-2.5 py-1 text-[11px] font-medium text-text-secondary hover:text-text-primary rounded-md';
                    }
                }
            });
        },

        renderNotificationFeed: function (filter = 'all') {
            const listEl = document.getElementById('notification-items-list');
            if (!listEl) return;

            const items = GoalieEnterprise.state.notifications.filter(n => {
                if (filter === 'all') return true;
                return n.type === filter;
            });

            if (items.length === 0) {
                listEl.innerHTML = `
                    <div class="p-6 text-center text-text-secondary text-xs">
                        <svg class="w-8 h-8 mx-auto mb-2 text-text-secondary/50" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/></svg>
                        Tidak ada notifikasi aktif.
                    </div>
                `;
                return;
            }

            listEl.innerHTML = items.map(n => {
                const borderClass = n.priority === 'high' ? 'border-l-4 border-l-red-500' : (n.priority === 'medium' ? 'border-l-4 border-l-amber-500' : 'border-l-4 border-l-emerald-500');
                const badgeColor = n.type === 'alert' ? 'bg-red-500/10 text-red-600 dark:text-red-400' : 'bg-blue-500/10 text-blue-600 dark:text-blue-400';
                const typeLabel = n.type === 'alert' ? 'PERINGATAN' : 'PENGINGAT';

                return `
                    <div class="p-3 bg-surface-subtle border border-border rounded-lg ${borderClass} transition-colors">
                        <div class="flex items-center justify-between gap-2 mb-1">
                            <span class="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded ${badgeColor}">${typeLabel}</span>
                            <span class="text-[9px] font-mono text-text-secondary">${new Date(n.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                        </div>
                        <h4 class="text-xs font-bold text-text-primary mb-0.5">${n.title}</h4>
                        <p class="text-[11px] text-text-secondary leading-snug">${n.message}</p>
                    </div>
                `;
            }).join('');
        },

        updateNotificationBadge: function () {
            const badge = document.getElementById('nav-notif-badge');
            if (!badge) return;
            const count = GoalieEnterprise.state.unreadNotifications;
            if (count > 0) {
                badge.textContent = count;
                badge.classList.remove('hidden');
            } else {
                badge.classList.add('hidden');
            }
        },

        markAllAsRead: async function () {
            try {
                const apiBase = window.API_BASE || '/golie/api/v1';
                await fetch(`${apiBase}/notifications/read`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ all: true })
                });
                GoalieEnterprise.state.unreadNotifications = 0;
                GoalieEnterprise.updateNotificationBadge();
                if (window.toast) window.toast.success('Pusat Notifikasi', 'Semua notifikasi telah ditandai dibaca.');
            } catch (e) {}
        },

        // ══════════════════════════════════════════════════════════
        // 7. USER MANAGEMENT & TEAM
        // ══════════════════════════════════════════════════════════
        openUserManagementModal: async function () {
            const modal = document.getElementById('user-management-modal');
            if (!modal) return;
            modal.classList.remove('hidden');
            if (window.GoalieMobile) window.GoalieMobile.triggerHaptic('selection');

            try {
                const apiBase = window.API_BASE || '/golie/api/v1';
                const headers = (typeof window.getAuthHeaders === 'function') ? window.getAuthHeaders() : {};
                const res = await fetch(`${apiBase}/team/squad`, { headers });
                if (res.ok) {
                    const data = await res.json();
                    GoalieEnterprise.renderTeamSquad(data.members || []);
                }
            } catch (e) {
                console.warn('[Goalie] Team squad fetch warning:', e);
            }
        },

        closeUserManagementModal: function () {
            const modal = document.getElementById('user-management-modal');
            if (modal) modal.classList.add('hidden');
        },

        renderTeamSquad: function (members) {
            const container = document.getElementById('team-members-table-body');
            if (!container) return;
            container.innerHTML = members.map(m => `
                <tr class="border-b border-border/60 text-xs">
                    <td class="py-2.5 px-3">
                        <div class="font-bold text-text-primary">${m.name}</div>
                        <div class="text-[10px] font-mono text-text-secondary">${m.email}</div>
                    </td>
                    <td class="py-2.5 px-3">
                        <span class="px-2 py-0.5 rounded font-mono text-[10px] font-bold ${m.role === 'head_coach' ? 'bg-tertiary/10 text-tertiary border border-tertiary/30' : 'bg-surface text-text-secondary border border-border'}">
                            ${m.role_title}
                        </span>
                    </td>
                    <td class="py-2.5 px-3 font-mono text-[10px] text-text-secondary hidden sm:table-cell">
                        ${m.permissions.join(', ')}
                    </td>
                    <td class="py-2.5 px-3 text-right">
                        <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-bold">Aktif</span>
                    </td>
                </tr>
            `).join('');
        },

        submitTeamInvite: async function (e) {
            if (e) e.preventDefault();
            const emailInput = document.getElementById('team-invite-email');
            const roleInput = document.getElementById('team-invite-role');
            if (!emailInput || !emailInput.value) return;

            const email = emailInput.value.trim();
            const role = roleInput ? roleInput.value : 'athlete';

            try {
                const apiBase = window.API_BASE || '/golie/api/v1';
                const res = await fetch(`${apiBase}/team/invite`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, role, team_name: 'Goalie Jakarta Racing Squad' })
                });
                const data = await res.json();
                if (window.toast) window.toast.success('Undangan Terkirim', `Kode undangan ${data.invite_code} dibuat untuk ${email}.`);
                emailInput.value = '';
            } catch (err) {
                if (window.toast) window.toast.error('Gagal Mengirim', 'Terjadi kesalahan pengiriman undangan.');
            }
        },

        // ══════════════════════════════════════════════════════════
        // 9. ANALYTICS & REPORTS SUITE
        // ══════════════════════════════════════════════════════════
        openAnalyticsReportsModal: function () {
            const modal = document.getElementById('analytics-reports-modal');
            if (!modal) return;
            modal.classList.remove('hidden');
            if (window.GoalieMobile) window.GoalieMobile.triggerHaptic('selection');
            GoalieEnterprise.generatePerformanceDigest();
        },

        closeAnalyticsReportsModal: function () {
            const modal = document.getElementById('analytics-reports-modal');
            if (modal) modal.classList.add('hidden');
        },

        generatePerformanceDigest: function () {
            const summaryBox = document.getElementById('analytics-digest-summary');
            if (!summaryBox) return;

            const cData = window.cockpitData || {};
            const weeklyKm = (cData.summaryGoal || 68.4).toFixed(1);
            const drift = (cData.cardiacDrift || 7.9).toFixed(1);
            const workoutsCount = cData.totalWorkouts || 14;

            summaryBox.innerHTML = `
                <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div class="p-3 bg-surface border border-border rounded-xl">
                        <span class="text-[10px] font-mono text-text-secondary uppercase block">Volume Mingguan</span>
                        <strong class="text-base font-bold text-text-primary font-mono">${weeklyKm} km</strong>
                        <span class="text-[10px] text-emerald-600 dark:text-emerald-400 block mt-0.5">+4.2% vs baseline</span>
                    </div>
                    <div class="p-3 bg-surface border border-border rounded-xl">
                        <span class="text-[10px] font-mono text-text-secondary uppercase block">Cardiac Drift</span>
                        <strong class="text-base font-bold text-text-primary font-mono">${drift}%</strong>
                        <span class="text-[10px] text-tertiary block mt-0.5">Aerobic Efficiency</span>
                    </div>
                    <div class="p-3 bg-surface border border-border rounded-xl">
                        <span class="text-[10px] font-mono text-text-secondary uppercase block">Rasio ACWR</span>
                        <strong class="text-base font-bold text-text-primary font-mono">1.08</strong>
                        <span class="text-[10px] text-emerald-600 dark:text-emerald-400 block mt-0.5">Optimal Sweet Spot</span>
                    </div>
                    <div class="p-3 bg-surface border border-border rounded-xl">
                        <span class="text-[10px] font-mono text-text-secondary uppercase block">Sesi Tercatat</span>
                        <strong class="text-base font-bold text-text-primary font-mono">${workoutsCount}</strong>
                        <span class="text-[10px] text-text-secondary block mt-0.5">Garmin &amp; Strava</span>
                    </div>
                </div>
            `;
        },

        downloadAnalyticsCsv: function () {
            const cData = window.cockpitData || {};
            const csvRows = [
                ["Metrik", "Nilai", "Satuan"],
                ["Volume Latihan", cData.summaryGoal || 68.4, "km"],
                ["Total Kalori Terbakar", cData.calorieLoss || 4957, "kkal"],
                ["Cardiac Drift Pw:HR", cData.cardiacDrift || 7.9, "persen"],
                ["Jumlah Sesi", cData.totalWorkouts || 14, "sesi"],
                ["Status ACWR", "1.08", "ratio"]
            ];

            const csvContent = "data:text/csv;charset=utf-8," + csvRows.map(e => e.join(",")).join("\n");
            const encodedUri = encodeURI(csvContent);
            const link = document.createElement("a");
            link.setAttribute("href", encodedUri);
            link.setAttribute("download", `goalie_analytics_report_${new Date().toISOString().split('T')[0]}.csv`);
            document.body.appendChild(link);
            link.click();
            link.remove();
            if (window.toast) window.toast.success('Laporan Diunduh', 'Berkas CSV analitik performa atletik berhasil diunduh.');
        },

        // ══════════════════════════════════════════════════════════
        // 10. BILLING & INVOICES
        // ══════════════════════════════════════════════════════════
        openBillingHubModal: async function () {
            const modal = document.getElementById('billing-hub-modal');
            if (!modal) return;
            modal.classList.remove('hidden');
            if (window.GoalieMobile) window.GoalieMobile.triggerHaptic('selection');

            try {
                const apiBase = window.API_BASE || '/golie/api/v1';
                const headers = (typeof window.getAuthHeaders === 'function') ? window.getAuthHeaders() : {};
                const res = await fetch(`${apiBase}/billing/invoices`, { headers });
                if (res.ok) {
                    const data = await res.json();
                    GoalieEnterprise.renderInvoicesTable(data.invoices || []);
                }
            } catch (e) {
                console.warn('[Goalie] Invoices fetch warning:', e);
            }
        },

        closeBillingHubModal: function () {
            const modal = document.getElementById('billing-hub-modal');
            if (modal) modal.classList.add('hidden');
        },

        renderInvoicesTable: function (invoices) {
            const tbody = document.getElementById('billing-invoices-tbody');
            if (!tbody) return;
            tbody.innerHTML = invoices.map(inv => `
                <tr class="border-b border-border/60 text-xs">
                    <td class="py-2.5 px-3 font-mono font-bold text-text-primary">${inv.id}</td>
                    <td class="py-2.5 px-3 font-mono text-text-secondary">${inv.date}</td>
                    <td class="py-2.5 px-3">${inv.description}</td>
                    <td class="py-2.5 px-3 font-mono font-bold text-text-primary">${inv.amount_formatted}</td>
                    <td class="py-2.5 px-3 text-right">
                        <span class="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-mono text-[10px] font-bold">LUNAS</span>
                    </td>
                </tr>
            `).join('');
        },

        // ══════════════════════════════════════════════════════════
        // 11. HELP & SUPPORT CENTER
        // ══════════════════════════════════════════════════════════
        openSupportCenterModal: function () {
            const modal = document.getElementById('support-center-modal');
            if (!modal) return;
            modal.classList.remove('hidden');
            if (window.GoalieMobile) window.GoalieMobile.triggerHaptic('selection');
        },

        closeSupportCenterModal: function () {
            const modal = document.getElementById('support-center-modal');
            if (modal) modal.classList.add('hidden');
        },

        submitSupportFeedback: async function (e) {
            if (e) e.preventDefault();
            const category = document.getElementById('support-feedback-category')?.value || 'feature_request';
            const subject = document.getElementById('support-feedback-subject')?.value || 'Masukan Atlet';
            const message = document.getElementById('support-feedback-message')?.value || '';

            if (!message.trim()) {
                if (window.toast) window.toast.warning('Pesan Diperlukan', 'Tuliskan masukan atau kendala yang Anda alami.');
                return;
            }

            try {
                const apiBase = window.API_BASE || '/golie/api/v1';
                await fetch(`${apiBase}/support/feedback`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ category, subject, message, rating: 5 })
                });

                if (window.toast) window.toast.success('Masukan Terkirim', 'Terima kasih atas kontribusi Anda dalam pengembangan Goalie.');
                document.getElementById('support-feedback-message').value = '';
                GoalieEnterprise.closeSupportCenterModal();
            } catch (err) {
                if (window.toast) window.toast.error('Gagal Mengirim', 'Terjadi gangguan jaringan saat mengirim masukan.');
            }
        },

        // ══════════════════════════════════════════════════════════
        // 12. SYSTEM PAGES & ERROR BOUNDARIES (404, 403, 500, etc.)
        // ══════════════════════════════════════════════════════════
        showSystemPage: function (type) {
            const overlay = document.getElementById('system-page-overlay');
            if (!overlay) return;

            const configs = {
                '404': {
                    code: '404',
                    title: 'Halaman Tidak Ditemukan',
                    desc: 'Jalur tautan atau rute telemetri yang Anda tuju tidak tersedia dalam workstation ini.',
                    actionLabel: 'Kembali ke Cockpit',
                    action: () => { GoalieEnterprise.closeSystemPage(); if (typeof window.switchWorkstationTab === 'function') window.switchWorkstationTab('cockpit'); }
                },
                '403': {
                    code: '403',
                    title: 'Akses Dibatasi (Forbidden)',
                    desc: 'Fitur ini memerlukan hak akses Head Coach atau langganan Goalie Pro Athlete aktif.',
                    actionLabel: 'Buka Manajemen Lisensi',
                    action: () => { GoalieEnterprise.closeSystemPage(); GoalieEnterprise.openBillingHubModal(); }
                },
                '500': {
                    code: '500',
                    title: 'Kendala Layanan Internal',
                    desc: 'Mesin komputasi mengalami hambatan saat memproses telemetri. Data aman di penyimpanan lokal.',
                    actionLabel: 'Muat Ulang Halaman',
                    action: () => { window.location.reload(); }
                },
                'maintenance': {
                    code: 'MAINTENANCE',
                    title: 'Pemeliharaan Sistem Terjadwal',
                    desc: 'Sinkronisasi Garmin dan server komputasi sedang diperbarui untuk peningkatan performa.',
                    actionLabel: 'Cek Status Server',
                    action: () => { window.location.reload(); }
                },
                'offline': {
                    code: 'OFFLINE',
                    title: 'Koneksi Internet Terputus',
                    desc: 'Aplikasi beroperasi dalam mode cache lokal mandiri. Latihan yang dicatat akan disinkronkan otomatis saat online.',
                    actionLabel: 'Tutup & Lanjutkan Latihan',
                    action: () => { GoalieEnterprise.closeSystemPage(); }
                },
                'session_expired': {
                    code: 'AUTH EXPIRED',
                    title: 'Sesi Masuk Berakhir',
                    desc: 'Otorisasi token keamanan telah habis masa berlakunya. Silakan masuk kembali.',
                    actionLabel: 'Masuk Kembali (Login)',
                    action: () => { window.location.href = 'login'; }
                }
            };

            const cfg = configs[type] || configs['404'];
            document.getElementById('sys-page-code').textContent = cfg.code;
            document.getElementById('sys-page-title').textContent = cfg.title;
            document.getElementById('sys-page-desc').textContent = cfg.desc;
            
            const actionBtn = document.getElementById('sys-page-action-btn');
            actionBtn.textContent = cfg.actionLabel;
            actionBtn.onclick = cfg.action;

            overlay.classList.remove('hidden');
            if (window.GoalieMobile) window.GoalieMobile.triggerHaptic('warning');
        },

        closeSystemPage: function () {
            const overlay = document.getElementById('system-page-overlay');
            if (overlay) overlay.classList.add('hidden');
        }
    };

    window.GoalieEnterprise = GoalieEnterprise;

    document.addEventListener('DOMContentLoaded', function () {
        GoalieEnterprise.fetchNotifications();
    });

})(typeof window !== 'undefined' ? window : this);
