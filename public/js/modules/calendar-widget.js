/**
 * Goalie AI Weekly Calendar Widget
 * Deterministic Sports Engine & Dual Gemini AI Training Calendar
 * 
 * Fitur:
 * 1. Visualisasi 7-Hari Polarisasi Latihan (Senin - Minggu).
 * 2. Terisi otomatis dari WeeklyCalendarService (Sports Engine + AI).
 * 3. Indikator Sesi Kunci, Zona Latihan Karvonen, Jarak & Target Pace.
 * 4. Panel Detail Preskripsi (Pemanasan, Sesi Utama, Pendinginan, Nutrisi & Fisiologi).
 * 5. Interaksi: Toggle Selesai, Diskusi Coach AI, Ekspor .ICS.
 */

(function (root, factory) {
    if (typeof define === 'function' && define.amd) {
        define([], factory);
    } else if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else {
        root.GoalieCalendarWidget = factory();
    }
}(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    let _currentWeekOffset = 0;
    let _calendarData = null;
    let _selectedDayIndex = null;
    let _isLoading = false;

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

    function escapeHTML(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    /**
     * Memuat data jadwal kalender mingguan dari backend
     */
    async function fetchWeeklySchedule(offset = 0, force = false) {
        _currentWeekOffset = offset;
        _isLoading = true;
        renderAllWidgets();

        try {
            const apiBase = getApiBase();
            const res = await fetch(`${apiBase}/training/weekly-calendar?week_offset=${offset}&force_regenerate=${force}`, {
                headers: getAuthHeaders()
            });

            if (!res.ok) throw new Error('Gagal mengambil jadwal kalender latihan.');
            const data = await res.json();
            _calendarData = data;

            // Jika belum ada hari yang dipilih, pilih hari ini secara default
            if (_selectedDayIndex === null && data.days) {
                const todayIdx = data.days.findIndex(d => d.is_today);
                _selectedDayIndex = todayIdx >= 0 ? todayIdx : 0;
            }

            // Sync ke appState global jika ada
            if (typeof window.currentWeeklyCalendarData !== 'undefined') {
                window.currentWeeklyCalendarData = data;
            }
        } catch (err) {
            console.error('[GoalieCalendarWidget] Fetch error:', err);
        } finally {
            _isLoading = false;
            renderAllWidgets();
        }
    }

    /**
     * Merender widget kalender pada seluruh container yang terdaftar
     */
    function renderAllWidgets() {
        const containers = document.querySelectorAll('.goalie-calendar-widget-mount');
        containers.forEach(container => renderWidgetTo(container));
    }

    /**
     * Render widget ke elemen spesifik
     */
    function renderWidgetTo(container) {
        if (!container) return;

        if (_isLoading && !_calendarData) {
            container.innerHTML = `
                <div class="flat-card border border-border/80 p-6 bg-surface rounded-2xl flex flex-col items-center justify-center space-y-3 min-h-[220px]">
                    <div class="w-8 h-8 rounded-full border-2 border-tertiary border-t-transparent animate-spin"></div>
                    <p class="text-xs font-mono text-text-secondary">Menyiapkan kalender latihan AI &amp; Sports Engine...</p>
                </div>
            `;
            return;
        }

        const data = _calendarData || getFallbackData();
        const days = data.days || [];
        const weekRange = data.week_range_formatted || 'Minggu Latihan Aktif';
        const totalKm = data.total_planned_km || 0;
        const totalHours = data.total_planned_hours || (Math.round((data.total_planned_duration_min || 0) / 60 * 10) / 10);
        const qualityCount = data.quality_sessions_count || 0;
        const recoveryCount = data.recovery_days_count || 0;
        const directive = data.ai_directive || 'Fokus pada adaptasi aerobik dasar dan pemeliharaan ritme kardiovaskular.';

        const zonePills = {
            'Z1': 'bg-slate-500/10 text-slate-700 dark:text-slate-300 border-slate-500/30',
            'Z2': 'bg-sky-500/10 text-sky-700 dark:text-sky-300 border-sky-500/30',
            'Z3': 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30',
            'Z4': 'bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/30',
            'Z5': 'bg-rose-500/10 text-rose-700 dark:text-rose-300 border-rose-500/30'
        };

        const selectedDay = (_selectedDayIndex !== null && days[_selectedDayIndex]) ? days[_selectedDayIndex] : days[0];

        let html = `
        <div class="flat-card border border-border/80 p-4 sm:p-5 bg-surface rounded-2xl space-y-4 shadow-xs transition-all duration-200">
            <!-- Header Bar -->
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border/70 pb-3.5">
                <div>
                    <div class="flex flex-wrap items-center gap-2">
                        <span class="w-7 h-7 rounded-lg bg-tertiary/10 border border-tertiary/30 text-tertiary flex items-center justify-center font-bold text-xs shrink-0">
                            📅
                        </span>
                        <h3 class="font-display font-bold text-sm sm:text-base text-text-primary">
                            Kalender Latihan Mingguan AI
                        </h3>
                        <span class="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-bold border border-emerald-500/20">
                            SPORTS ENGINE TERISI
                        </span>
                    </div>
                    <div class="text-[11px] font-mono text-text-secondary mt-1 flex flex-wrap items-center gap-2">
                        <span class="font-bold text-text-primary">${escapeHTML(weekRange)}</span>
                        <span>•</span>
                        <span>${totalKm} km terencana</span>
                        <span>•</span>
                        <span>${qualityCount} sesi kunci</span>
                        <span>•</span>
                        <span>${recoveryCount} recovery</span>
                    </div>
                </div>

                <!-- Navigation Controls -->
                <div class="flex items-center gap-1.5 self-start sm:self-center font-mono text-xs">
                    <button type="button" onclick="GoalieCalendarWidget.changeWeek(-1)" class="w-8 h-8 rounded-lg bg-surface-subtle hover:bg-surface border border-border text-text-primary flex items-center justify-center transition-colors" title="Minggu Sebelumnya">
                        <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 19l-7-7 7-7"/></svg>
                    </button>
                    <button type="button" onclick="GoalieCalendarWidget.resetWeek()" class="px-2.5 h-8 rounded-lg ${(_currentWeekOffset === 0) ? 'bg-tertiary text-white font-bold' : 'bg-surface-subtle hover:bg-surface text-text-secondary'} border border-border text-[11px] font-bold transition-colors">
                        Minggu Ini
                    </button>
                    <button type="button" onclick="GoalieCalendarWidget.changeWeek(1)" class="w-8 h-8 rounded-lg bg-surface-subtle hover:bg-surface border border-border text-text-primary flex items-center justify-center transition-colors" title="Minggu Berikutnya">
                        <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 5l7 7-7 7"/></svg>
                    </button>
                    <button type="button" onclick="GoalieCalendarWidget.regenerate()" class="h-8 px-2.5 rounded-lg bg-surface-subtle hover:bg-surface border border-border text-text-primary hover:text-tertiary text-[11px] flex items-center gap-1 transition-colors ml-1" title="Kalibrasi ulang dengan AI Coach">
                        <svg class="w-3 h-3 text-tertiary" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
                        <span class="hidden md:inline">Regenerasi AI</span>
                    </button>
                    <button type="button" onclick="GoalieCalendarWidget.downloadICS()" class="h-8 px-2.5 rounded-lg bg-tertiary/10 hover:bg-tertiary/20 text-tertiary border border-tertiary/30 text-[11px] font-bold flex items-center gap-1 transition-colors" title="Ekspor Kalender .ICS (Apple &amp; Google Calendar)">
                        <svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
                        <span class="hidden sm:inline">.ICS</span>
                    </button>
                </div>
            </div>

            <!-- AI Coach Directive Micro-Alert -->
            <div class="p-2.5 sm:p-3 rounded-xl bg-surface-subtle border border-border/80 flex items-start gap-2.5 text-xs text-text-secondary leading-relaxed">
                <span class="w-5 h-5 rounded-md bg-tertiary/15 text-tertiary flex items-center justify-center shrink-0 text-xs font-bold mt-0.5">
                    💡
                </span>
                <div>
                    <strong class="text-text-primary mr-1 font-display">Arahan Pelatih AI:</strong>
                    <span>${escapeHTML(directive)}</span>
                </div>
            </div>

            <!-- 7-Day Responsive Day Cards Strip -->
            <div class="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2.5">
        `;

        days.forEach((day, idx) => {
            const isSelected = _selectedDayIndex === idx;
            const isToday = Boolean(day.is_today);
            const isDone = Boolean(day.completed);
            const dist = parseFloat(day.distance_km || 0);
            const distStr = dist > 0 ? `${dist.toFixed(1)} km` : (day.duration_min ? `${day.duration_min}m` : 'Rest');
            const dayName = (day.day_name_id || day.day_name || 'Hari').slice(0, 3).toUpperCase();
            
            // Format tanggal hari (misal: "14 Nov")
            let dateNum = '';
            try {
                const d = new Date(day.date);
                dateNum = isNaN(d.getDate()) ? '' : `${d.getDate()} ${d.toLocaleDateString('id-ID', { month: 'short' })}`;
            } catch (e) {
                dateNum = day.date || '';
            }

            // Sport & Category Icon
            const cat = String(day.category || '').toLowerCase();
            const wType = String(day.workout_type || '').toLowerCase();
            let icon = '🏃';
            if (cat.includes('long') || wType.includes('long')) icon = '⛰️';
            else if (cat.includes('interval') || cat.includes('threshold') || cat.includes('tempo')) icon = '⚡';
            else if (cat.includes('strength') || wType.includes('strength')) icon = '🏋️';
            else if (cat.includes('recovery') || cat.includes('rest') || dist === 0) icon = '🧘';

            // Zone tag style
            const zKey = (day.intensity_zone || 'Z2').split(' ')[0].split('-')[0];
            const zoneCls = zonePills[zKey] || 'bg-surface-subtle text-text-secondary border-border';

            let cardStateClasses = 'border-border/70 hover:border-text-primary/60 bg-surface';
            if (isSelected) {
                cardStateClasses = 'border-tertiary ring-2 ring-tertiary/20 bg-tertiary/5 shadow-xs';
            } else if (isToday) {
                cardStateClasses = 'border-tertiary/80 bg-surface';
            }

            html += `
                <div onclick="GoalieCalendarWidget.selectDay(${idx})" class="p-3 rounded-xl border ${cardStateClasses} cursor-pointer transition-all duration-150 flex flex-col justify-between min-h-[145px] group select-none">
                    <!-- Day Name & Today Indicator -->
                    <div>
                        <div class="flex items-center justify-between border-b border-border/50 pb-1.5 mb-2">
                            <span class="font-display font-extrabold text-[11px] text-text-primary tracking-wider">${dayName}</span>
                            <span class="text-[10px] font-mono text-text-secondary">${dateNum}</span>
                        </div>

                        <!-- Workout Title & Icon -->
                        <div class="space-y-1 mb-2">
                            <div class="flex items-center gap-1.5 text-xs font-bold text-text-primary group-hover:text-tertiary transition-colors truncate">
                                <span>${icon}</span>
                                <span class="truncate">${escapeHTML(day.title || 'Latihan')}</span>
                            </div>
                            <div class="text-[11px] font-mono text-text-secondary flex items-center justify-between">
                                <span class="font-bold text-text-primary">${distStr}</span>
                                ${day.target_pace ? `<span class="text-[10px] text-text-secondary truncate">@ ${escapeHTML(day.target_pace.split('-')[0])}</span>` : ''}
                            </div>
                        </div>
                    </div>

                    <!-- Bottom Status Tag & Zone -->
                    <div class="pt-2 border-t border-border/50 flex items-center justify-between mt-auto text-[10px] font-mono">
                        <span class="px-1.5 py-0.2 rounded border font-semibold ${zoneCls}">
                            ${escapeHTML((day.intensity_zone || 'Z2').split(' ')[0])}
                        </span>
                        ${isDone 
                            ? '<span class="text-emerald-500 font-bold flex items-center gap-0.5">✓ Beres</span>'
                            : (isToday 
                                ? '<span class="px-1.5 py-0.2 rounded-full bg-tertiary text-white font-bold text-[9px] animate-pulse">HARI INI</span>' 
                                : '<span class="text-text-secondary">Plan</span>'
                            )
                        }
                    </div>
                </div>
            `;
        });

        html += `
            </div>

            <!-- Expandable Selected Day Execution Brief -->
            ${selectedDay ? renderDayDetailBrief(selectedDay, _selectedDayIndex) : ''}
        </div>
        `;

        container.innerHTML = html;
    }

    /**
     * Detail kartu latihan yang sedang dipilih
     */
    function renderDayDetailBrief(day, idx) {
        const isDone = Boolean(day.completed);
        const pace = day.target_pace || 'Santai / Conversational';
        const hr = day.target_hr_range || 'Zona 2 Aerobik (125-145 bpm)';
        const dist = day.distance_km ? `${day.distance_km} km` : (day.duration_min ? `${day.duration_min} menit` : 'Istirahat Total');
        const warmup = day.warmup || '5-10 menit pemanasan dinamis & mobilitas pergelangan kaki';
        const mainSet = day.main_set || day.description || 'Lari aerobik konsisten sesuai target zona detak jantung';
        const cooldown = day.cooldown || '5 menit jalan santai & peregangan statis paha/betis';
        const nutrition = day.fueling_guidance || 'Pastikan hidrasi air putih sebelum sesi dan asupan elektrolit ringan.';
        const rationale = day.ai_coach_rationale || 'Membangun kapasitas mitokondria dan kekuatan otot tanpa membebani sistem saraf pusat.';

        return `
            <div class="p-4 rounded-xl bg-surface-subtle border border-border/80 space-y-3.5 transition-all">
                <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border/70 pb-2.5">
                    <div class="flex items-center gap-2">
                        <span class="px-2 py-0.5 rounded-full bg-tertiary text-white font-mono text-[10px] font-bold">
                            ${escapeHTML((day.day_name_id || day.day_name || 'HARI').toUpperCase())}
                        </span>
                        <h4 class="font-display font-bold text-sm text-text-primary">
                            ${escapeHTML(day.title || 'Detail Sesi Latihan')}
                        </h4>
                    </div>
                    <div class="flex items-center gap-2 self-start sm:self-auto font-mono text-xs">
                        <span class="text-text-secondary">Target:</span>
                        <strong class="text-tertiary">${dist}</strong>
                        <span>•</span>
                        <span class="text-text-secondary">Pace:</span>
                        <strong class="text-text-primary">${escapeHTML(pace)}</strong>
                    </div>
                </div>

                <!-- Structured Workout Blocks -->
                <div class="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                    <div class="p-2.5 rounded-lg bg-surface border border-border space-y-1">
                        <span class="text-[10px] font-mono uppercase tracking-wider text-text-secondary font-bold block">1. Pemanasan</span>
                        <p class="text-text-primary leading-relaxed">${escapeHTML(warmup)}</p>
                    </div>
                    <div class="p-2.5 rounded-lg bg-surface border border-border space-y-1">
                        <span class="text-[10px] font-mono uppercase tracking-wider text-tertiary font-bold block">2. Sesi Utama (Main Set)</span>
                        <p class="text-text-primary font-medium leading-relaxed">${escapeHTML(mainSet)}</p>
                    </div>
                    <div class="p-2.5 rounded-lg bg-surface border border-border space-y-1">
                        <span class="text-[10px] font-mono uppercase tracking-wider text-text-secondary font-bold block">3. Pendinginan</span>
                        <p class="text-text-primary leading-relaxed">${escapeHTML(cooldown)}</p>
                    </div>
                </div>

                <!-- Scientific Coach Rationale & Nutrition -->
                <div class="p-3 rounded-lg bg-surface border border-border/80 text-xs space-y-1.5">
                    <div class="flex items-center gap-1.5 text-text-secondary font-mono text-[11px]">
                        <span class="font-bold text-text-primary">Fisiologi Latihan &amp; Target HR:</span>
                        <span class="text-tertiary">${escapeHTML(hr)}</span>
                    </div>
                    <p class="text-text-secondary leading-relaxed">${escapeHTML(rationale)}</p>
                    <div class="pt-1.5 border-t border-border/60 text-[11px] text-text-secondary flex items-center gap-1.5">
                        <span class="font-bold text-text-primary font-mono">Nutrisi &amp; Hidrasi:</span>
                        <span>${escapeHTML(nutrition)}</span>
                    </div>
                </div>

                <!-- Action Bar -->
                <div class="flex flex-wrap items-center justify-between gap-2 pt-1">
                    <div class="flex items-center gap-2">
                        <button type="button" onclick="GoalieCalendarWidget.toggleCompletion(${idx})" class="px-3.5 py-1.5 rounded-lg ${isDone ? 'bg-surface hover:bg-surface-subtle text-text-secondary border border-border' : 'bg-emerald-600 text-white font-bold shadow-xs hover:bg-emerald-700'} text-xs font-mono transition-colors flex items-center gap-1.5">
                            <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                            <span>${isDone ? 'Kembalikan ke Terencana' : 'Tandai Selesai'}</span>
                        </button>
                        <button type="button" onclick="GoalieCalendarWidget.askCoachAboutDay(${idx})" class="px-3 py-1.5 rounded-lg bg-surface hover:bg-surface-subtle border border-border text-text-primary text-xs font-mono flex items-center gap-1.5 transition-colors">
                            <svg class="w-3.5 h-3.5 text-tertiary" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                            <span>Tanya Coach AI</span>
                        </button>
                    </div>
                    <span class="text-[11px] font-mono text-text-secondary">
                        Sesi ID: <strong class="text-text-primary">${escapeHTML(day.workout_id || `sched_${idx}`)}</strong>
                    </span>
                </div>
            </div>
        `;
    }

    /**
     * Ganti hari yang dipilih
     */
    function selectDay(idx) {
        _selectedDayIndex = idx;
        renderAllWidgets();
    }

    /**
     * Navigasi minggu
     */
    function changeWeek(direction) {
        fetchWeeklySchedule(_currentWeekOffset + direction);
    }

    function resetWeek() {
        fetchWeeklySchedule(0);
    }

    /**
     * Regenerasi jadwal AI
     */
    async function regenerateSchedule() {
        if (typeof toast !== 'undefined' && typeof toast.loading === 'function') {
            const loadToast = toast.loading('Regenerasi AI', 'Menghitung ulang periodisasi 7 hari dari sports engine...');
            await fetchWeeklySchedule(_currentWeekOffset, true);
            loadToast.dismiss();
            if (typeof toast.success === 'function') {
                toast.success('Kalender Terkalibrasi', 'Jadwal latihan 7 hari berhasil disesuaikan secara ilmiah.');
            }
        } else {
            await fetchWeeklySchedule(_currentWeekOffset, true);
        }
    }

    /**
     * Toggle status selesai hari ini
     */
    async function toggleCompletion(idx) {
        if (!_calendarData || !_calendarData.days || !_calendarData.days[idx]) return;
        const day = _calendarData.days[idx];
        const apiBase = getApiBase();

        try {
            const res = await fetch(`${apiBase}/training/weekly-calendar/toggle-day`, {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({
                    week_key: _calendarData.week_key,
                    day_index: idx
                })
            });

            if (res.ok) {
                const result = await res.json();
                day.completed = Boolean(result.completed);
                renderAllWidgets();
                if (typeof toast !== 'undefined' && typeof toast.success === 'function') {
                    toast.success('Status Terupdate', day.completed ? `Sesi ${day.day_name_id || day.day_name} ditandai selesai!` : 'Status dikembalikan ke terencana.');
                }
            }
        } catch (e) {
            console.error('Error toggling day:', e);
        }
    }

    /**
     * Buka percakapan dengan Coach AI mengenai sesi hari ini
     */
    function askCoachAboutDay(idx) {
        if (!_calendarData || !_calendarData.days || !_calendarData.days[idx]) return;
        const day = _calendarData.days[idx];
        
        if (typeof window.switchWorkstationTab === 'function') {
            window.switchWorkstationTab('chat');
        }

        const chatInput = document.getElementById('chat-input');
        if (chatInput) {
            chatInput.value = `Halo Coach! Berikan panduan eksekusi untuk sesi ${day.day_name_id || day.day_name} (${day.date}): "${day.title}". Target: ${day.distance_km || 5} km, Zona ${day.intensity_zone || 'Z2'}, Pace ${day.target_pace || 'santai'}. Bagaimana strategi detak jantung dan nutrisinya?`;
            chatInput.focus();
        }
    }

    /**
     * Download file .ICS kalender mingguan
     */
    async function downloadICS() {
        const apiBase = getApiBase();
        try {
            const res = await fetch(`${apiBase}/training/weekly-calendar/ical?week_offset=${_currentWeekOffset}`, {
                headers: getAuthHeaders()
            });
            if (!res.ok) throw new Error('Ekspor iCal gagal');
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `goalie_jadwal_latihan_offset_${_currentWeekOffset}.ics`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            if (typeof toast !== 'undefined' && typeof toast.success === 'function') {
                toast.success('Kalender Diekspor', 'File .ICS siap diimpor ke Apple Calendar atau Google Calendar.');
            }
        } catch (e) {
            if (typeof toast !== 'undefined' && typeof toast.error === 'function') {
                toast.error('Gagal Ekspor', e.message);
            }
        }
    }

    /**
     * Fallback data inisial jika offline
     */
    function getFallbackData() {
        return {
            week_key: "2026-W46",
            week_range_formatted: "09 Nov - 15 Nov 2026",
            total_planned_km: 42.1,
            total_planned_hours: 4.5,
            quality_sessions_count: 2,
            recovery_days_count: 2,
            ai_directive: "Fokus pada adaptasi ambang laktat & polarisasi volume Zone 2. Long run progresif 16K di akhir pekan.",
            days: [
                { day_index: 0, day_name_id: "Senin", date: "2026-11-09", is_today: false, is_past: true, completed: true, title: "Zone 2 Aerobic Foundation Run", category: "Base", intensity_zone: "Z2 (Aerobic Base)", distance_km: 6.7, target_pace: "06:45 - 07:15 /km", target_hr_range: "128-142 bpm" },
                { day_index: 1, day_name_id: "Selasa", date: "2026-11-10", is_today: false, is_past: true, completed: true, title: "Lactate Threshold 5x1000m Cruise", category: "Quality", intensity_zone: "Z4 (Threshold)", distance_km: 8.4, target_pace: "04:20 - 04:35 /km", target_hr_range: "162-170 bpm" },
                { day_index: 2, day_name_id: "Rabu", date: "2026-11-11", is_today: false, is_past: true, completed: true, title: "Active Mobility & Deep Core Stability", category: "Recovery", intensity_zone: "Z1 (Recovery)", distance_km: 0.0, duration_min: 45, target_pace: "Mobilitas Otot", target_hr_range: "<115 bpm" },
                { day_index: 3, day_name_id: "Kamis", date: "2026-11-12", is_today: false, is_past: true, completed: true, title: "Aerobic Build + 6 Neuromuscular Strides", category: "Steady", intensity_zone: "Z2-Z3 (Steady)", distance_km: 7.6, target_pace: "06:20 - 06:40 /km", target_hr_range: "135-148 bpm" },
                { day_index: 4, day_name_id: "Jumat", date: "2026-11-13", is_today: false, is_past: true, completed: true, title: "Rest Day & Sleep Optimization", category: "Rest", intensity_zone: "Z1 (Rest)", distance_km: 0.0, duration_min: 0, target_pace: "Istirahat Total", target_hr_range: "<100 bpm" },
                { day_index: 5, day_name_id: "Sabtu", date: "2026-11-14", is_today: true, is_past: false, completed: false, title: "Key Progressive Long Run", category: "Long Run", intensity_zone: "Z2-Z3 (Progressive)", distance_km: 16.0, target_pace: "06:15 - 06:35 /km", target_hr_range: "138-155 bpm" },
                { day_index: 6, day_name_id: "Minggu", date: "2026-11-15", is_today: false, is_past: false, completed: false, title: "Cross-Training / Gentle Flush Walk", category: "Recovery", intensity_zone: "Z1 (Active Recovery)", distance_km: 3.4, target_pace: "Santai", target_hr_range: "<120 bpm" }
            ]
        };
    }

    /**
     * Inisialisasi otomatis pada DOM Ready
     */
    function init() {
        renderAllWidgets();
        fetchWeeklySchedule(0);
    }

    if (typeof document !== 'undefined') {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
        } else {
            setTimeout(init, 100);
        }
    }

    return {
        init: init,
        fetch: fetchWeeklySchedule,
        render: renderAllWidgets,
        selectDay: selectDay,
        changeWeek: changeWeek,
        resetWeek: resetWeek,
        regenerate: regenerateSchedule,
        toggleCompletion: toggleCompletion,
        askCoachAboutDay: askCoachAboutDay,
        downloadICS: downloadICS,
        getData: () => _calendarData
    };
}));
