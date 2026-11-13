/**
 * Goalie Sports Physiology Math Module
 * Pure deterministic calculations for Karvonen HRR, Pace conversions,
 * Minetti GAP, and Course Fueling.
 */

(function (root, factory) {
    if (typeof define === 'function' && define.amd) {
        define([], factory);
    } else if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else {
        root.GoalieSportsMath = factory();
    }
}(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    function calculateKarvonenZones(restingHr, maxHr) {
        const rhr = Math.max(30, parseInt(restingHr) || 48);
        const mhr = Math.max(rhr + 20, parseInt(maxHr) || 192);
        const hrr = Math.max(0, mhr - rhr);

        const z1Max = Math.round(rhr + (hrr * 0.60));
        const z2Min = z1Max;
        const z2Max = Math.round(rhr + (hrr * 0.70));
        const z3Min = z2Max;
        const z3Max = Math.round(rhr + (hrr * 0.80));
        const z4Min = z3Max;
        const z4Max = Math.round(rhr + (hrr * 0.90));
        const z5Min = z4Max;

        return {
            hrr,
            zone1: { min: rhr, max: z1Max, label: 'Zone 1 (Active Recovery)' },
            zone2: { min: z2Min, max: z2Max, label: 'Zone 2 (Aerobic Base)' },
            zone3: { min: z3Min, max: z3Max, label: 'Zone 3 (Tempo Aerobic)' },
            zone4: { min: z4Min, max: z4Max, label: 'Zone 4 (Sub-Threshold / LT2)' },
            zone5: { min: z5Min, max: mhr, label: 'Zone 5 (VO2 Max / Speed)' }
        };
    }

    function paceToSeconds(paceStr) {
        if (!paceStr) return 0;
        const parts = String(paceStr).split(':');
        if (parts.length === 2) {
            return (parseInt(parts[0], 10) * 60) + parseInt(parts[1], 10);
        }
        const val = parseFloat(paceStr);
        return isNaN(val) ? 0 : Math.round(val * 60);
    }

    function secondsToPace(totalSeconds) {
        if (!totalSeconds || totalSeconds <= 0) return '00:00';
        const mins = Math.floor(totalSeconds / 60);
        const secs = Math.round(totalSeconds % 60);
        return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    }

    function calculateMinettiGap(paceSecPerKm, gradientPercent) {
        const i = (gradientPercent || 0) / 100.0;
        // Minetti polynomial energy cost ratio relative to flat running (i = 0 cost = 3.6 J/(kg*m))
        // C(i) = 155.4*i^5 - 30.4*i^4 - 43.3*i^3 + 46.3*i^2 + 19.5*i + 3.6
        const cost = (155.4 * Math.pow(i, 5)) - (30.4 * Math.pow(i, 4)) - (43.3 * Math.pow(i, 3)) + (46.3 * Math.pow(i, 2)) + (19.5 * i) + 3.6;
        const flatCost = 3.6;
        const costRatio = Math.max(0.5, cost / flatCost);
        const gapSeconds = Math.round(paceSecPerKm / costRatio);
        return {
            gapSeconds,
            gapFormatted: secondsToPace(gapSeconds),
            costRatio: parseFloat(costRatio.toFixed(3))
        };
    }

    return {
        calculateKarvonenZones,
        paceToSeconds,
        secondsToPace,
        calculateMinettiGap
    };
}));
