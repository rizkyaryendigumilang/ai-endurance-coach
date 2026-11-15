/**
 * Goalie Mobile Native & Offline Resilience Module
 * Provides haptic feedback, offline connectivity banner, and touch optimization.
 */

(function (window) {
    'use strict';

    const GoalieMobile = {
        /**
         * Trigger tactile haptic feedback on supporting mobile devices
         * @param {'light'|'medium'|'heavy'|'success'|'warning'|'selection'} type
         */
        triggerHaptic: function (type) {
            try {
                if (window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.Haptics) {
                    const Haptics = window.Capacitor.Plugins.Haptics;
                    if (type === 'light') Haptics.impact({ style: 'LIGHT' });
                    else if (type === 'medium') Haptics.impact({ style: 'MEDIUM' });
                    else if (type === 'heavy') Haptics.impact({ style: 'HEAVY' });
                    else if (type === 'selection') Haptics.selectionChanged();
                    else if (type === 'success') Haptics.notification({ type: 'SUCCESS' });
                    else if (type === 'warning') Haptics.notification({ type: 'WARNING' });
                    return;
                }
                // Web vibration API fallback
                if ('vibrate' in navigator) {
                    if (type === 'heavy' || type === 'warning') navigator.vibrate([20, 50, 20]);
                    else if (type === 'medium' || type === 'success') navigator.vibrate([15, 30, 15]);
                    else navigator.vibrate(10);
                }
            } catch (e) {
                // Ignore devices without haptic motor
            }
        },

        /**
         * Initialize network status listeners
         */
        initNetworkMonitor: function () {
            function updateOnlineStatus() {
                const isOnline = navigator.onLine;
                const statusPill = document.getElementById('network-offline-pill');
                if (!statusPill) return;

                if (isOnline) {
                    statusPill.classList.add('hidden');
                } else {
                    statusPill.classList.remove('hidden');
                    if (window.toast) {
                        window.toast.warning('Mode Offline Aktif', 'Koneksi internet terputus. Data jadwal dan profil tetap dapat diakses dari cache lokal.');
                    }
                }
            }

            window.addEventListener('online', updateOnlineStatus);
            window.addEventListener('offline', updateOnlineStatus);
            updateOnlineStatus();
        },

        /**
         * Initialize pull-to-refresh listener on activity container
         */
        initPullToRefresh: function (containerId, onRefresh) {
            const container = document.getElementById(containerId);
            if (!container) return;

            let touchStartY = 0;
            let touchEndY = 0;

            container.addEventListener('touchstart', function (e) {
                if (container.scrollTop === 0) {
                    touchStartY = e.touches[0].clientY;
                }
            }, { passive: true });

            container.addEventListener('touchend', function (e) {
                if (container.scrollTop === 0) {
                    touchEndY = e.changedTouches[0].clientY;
                    if (touchEndY - touchStartY > 100) {
                        GoalieMobile.triggerHaptic('medium');
                        if (typeof onRefresh === 'function') {
                            onRefresh();
                        }
                    }
                }
            }, { passive: true });
        },

        /**
         * Initialize swipe down to dismiss on mobile bottom sheets
         */
        initBottomSheetGestures: function () {
            const modals = [
                { id: 'activity-detail-modal', closeFn: () => { if (typeof window.closeActivityDetailModal === 'function') window.closeActivityDetailModal(); } },
                { id: 'log-workout-modal', closeFn: () => { if (typeof window.closeLogWorkoutModal === 'function') window.closeLogWorkoutModal(); } },
                { id: 'post-run-debrief-modal', closeFn: () => { if (typeof window.closePostRunDebriefModal === 'function') window.closePostRunDebriefModal(); } },
                { id: 'user-management-modal', closeFn: () => { if (window.GoalieEnterprise) window.GoalieEnterprise.closeUserManagementModal(); } },
                { id: 'analytics-reports-modal', closeFn: () => { if (window.GoalieEnterprise) window.GoalieEnterprise.closeAnalyticsReportsModal(); } },
                { id: 'billing-hub-modal', closeFn: () => { if (window.GoalieEnterprise) window.GoalieEnterprise.closeBillingHubModal(); } },
                { id: 'support-center-modal', closeFn: () => { if (window.GoalieEnterprise) window.GoalieEnterprise.closeSupportCenterModal(); } }
            ];

            modals.forEach(({ id, closeFn }) => {
                const modal = document.getElementById(id);
                if (!modal) return;
                const sheet = modal.querySelector('.flat-card') || modal.querySelector('.relative');
                if (!sheet) return;

                let startY = 0;
                let currentY = 0;
                let isDragging = false;

                sheet.addEventListener('touchstart', function (e) {
                    if (window.innerWidth >= 768) return;
                    if (sheet.scrollTop <= 5) {
                        startY = e.touches[0].clientY;
                        currentY = startY;
                        isDragging = true;
                    }
                }, { passive: true });

                sheet.addEventListener('touchmove', function (e) {
                    if (!isDragging || window.innerWidth >= 768) return;
                    currentY = e.touches[0].clientY;
                    const diffY = currentY - startY;
                    if (diffY > 0) {
                        sheet.style.transform = `translateY(${diffY * 0.75}px)`;
                    }
                }, { passive: true });

                sheet.addEventListener('touchend', function () {
                    if (!isDragging || window.innerWidth >= 768) return;
                    isDragging = false;
                    const diffY = currentY - startY;
                    sheet.style.transition = 'transform 200ms cubic-bezier(0.16, 1, 0.3, 1)';
                    if (diffY > 90) {
                        sheet.style.transform = 'translateY(100%)';
                        GoalieMobile.triggerHaptic('light');
                        setTimeout(() => {
                            sheet.style.transform = '';
                            sheet.style.transition = '';
                            closeFn();
                        }, 180);
                    } else {
                        sheet.style.transform = '';
                        setTimeout(() => {
                            sheet.style.transition = '';
                        }, 200);
                    }
                }, { passive: true });
            });
        }
    };

    window.GoalieMobile = GoalieMobile;

    document.addEventListener('DOMContentLoaded', function () {
        GoalieMobile.initNetworkMonitor();
        GoalieMobile.initBottomSheetGestures();
    });

})(typeof window !== 'undefined' ? window : this);
