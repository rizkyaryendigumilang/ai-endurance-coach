# GLOSSARY.md — AI Endurance Coach Domain Vocabulary

This document establishes the canonical terminology and physiological definitions for Goalie. All code symbols, tests, issue discussions, and UI copy must adhere to these definitions.

---

### VDOT
Jack Daniels' physiological score of running fitness derived from a race performance. It equates to effective $VO_2\text{max}$ combined with running economy. VDOT is used to determine exact training paces for Easy (E), Marathon (M), Threshold (T), Interval (I), and Repetition (R) paces.

### LT2 (Lactate Threshold 2 / Ambang Laktat 2)
The secondary lactate threshold where lactate production exceeds the body's maximum clearance rate (typically around Zone 4 or 85–90% $HR_{max}$). Also known as anaerobic threshold or steady-state tempo effort (~1-hour race pace).

### Karvonen HRR (Heart Rate Reserve)
Target heart rate formula accounting for resting heart rate ($HR_{rest}$) and maximum heart rate ($HR_{max}$):
$$HR_{target} = HR_{rest} + \% \times (HR_{max} - HR_{rest})$$
Used to establish individualized aerobic zones far more accurately than standard percentage of $HR_{max}$.

### ACWR (Acute:Chronic Workload Ratio)
The ratio of 7-day acute workload (representing short-term fatigue) to 28-day chronic workload (representing baseline fitness):
$$ACWR = \frac{\text{Acute Load (7 days)}}{\text{Chronic Load (28 days)}}$$
- **0.8 to 1.3**: Optimal progression (Sweet Spot).
- **1.3 to 1.5**: Overreaching / caution.
- **> 1.5**: Danger zone with high injury risk.

### GAP (Grade-Adjusted Pace)
The equivalent flat-ground running pace for a given incline or decline, based on the energetic cost curves established by Minetti et al. (2002). Uphill running incurs higher metabolic cost per meter; downhill running reduces cost up to ~-10% grade before eccentric braking increases effort.

### Magnus-Tetens Formula & Dew Point ($T_d$)
The psychrometric equation used to calculate dew point temperature ($T_d$) from dry-bulb temperature ($T$) and relative humidity ($RH$):
$$\gamma(T, RH) = \ln\left(\frac{RH}{100}\right) + \frac{17.625 \cdot T}{243.04 + T}$$
$$T_d = \frac{243.04 \cdot \gamma(T, RH)}{17.625 - \gamma(T, RH)}$$
Dew point is an absolute measure of atmospheric moisture. When $T_d > 20^\circ\text{C}$, sweat evaporation is severely impeded.

### Thermal-Humidity Index (THI / Indeks Beban Panas)
The sum of ambient temperature and dew point in °C (or °F):
$$THI = T + T_d$$
Used by Goalie to apply non-linear quadratic pace adjustments and calculate additional fluid/electrolyte replenishment requirements in tropical conditions.

### Aerobic Decoupling (Pw:HR / Pace:HR Drift)
The physiological divergence between mechanical output (pace or power) and internal cardiac cost (heart rate) across the two halves of a steady aerobic workout.
$$\text{Decoupling Rate} = \frac{\text{EF}_{\text{half1}} - \text{EF}_{\text{half2}}}{\text{EF}_{\text{half1}}} \times 100\%$$
Where $\text{EF} = \frac{\text{Speed (m/s)}}{\text{Heart Rate (bpm)}}$. A decoupling drift $\le 5\%$ indicates excellent aerobic stamina; $> 5\%$ indicates cardiac drift, dehydration, or glycogen depletion.

### The Wall (Late-Stage Fade KM 30+)
A specific severe pace degradation occurring past KM 28–30 in marathons, triggered by muscular glycogen depletion, elevated core body temperature, and neuromuscular fatigue. Guarded in Goalie by checking minimum run distance ($\ge 28\text{ km}$) and comparing pace splits between KM 1–30 vs KM 30+.

### Golden Rule of Missed Mileage
Kilometers missed during training must **never** be repaid or compounded onto subsequent weeks. Missed sessions are handled via the Life Happens Auto-Rebalancer:
- **Tier 1 (Anchor / Long Run)**: Shifted within the current week only if a 48-hour recovery buffer exists.
- **Tier 2 (Quality / Intervals)**: Shortened or downgraded to easy volume.
- **Tier 3 (Filler / Easy Run)**: Dropped immediately. Never sacrifice rest days to catch up on missed easy miles.

### 48-Hour Polarization Buffer
The mandatory sterile recovery window of 48 to 72 hours between high-intensity lower body strength sessions and key running workouts (such as weekend Long Runs) to eliminate Delayed Onset Muscle Soreness (DOMS) interference and preserve neuromuscular stride mechanics.

### 4 Marathon Strength Pillars
1. **Foundation & Structural Balance**: Core, glute medius, and single-leg stability.
2. **Economy & Tendon Stiffness**: Explosive calf, soleus, and Achilles tendon spring recoil.
3. **Postural Stability & Anti-Fatigue**: Thoracic posture and hamstring/quad resistance to late-stage collapse.
4. **Taper Maintenance**: Low-volume, high-neural activation during pre-race taper.

### 2–3 RIR (Reps in Reserve)
The standard training intensity ceiling for marathon strength training. Runners must finish each resistance set with 2 to 3 reps in reserve before technical failure, avoiding hypertrophy-inducing metabolic exhaustion while optimizing neuromuscular recruitment.

### True Execution Score
A 0–100% workout compliance metric combining:
1. **Volume Compliance (50%)**: Ratio of actual distance to planned distance (clamped at 100%).
2. **Pace Compliance (30%)**: Target pace bracket accuracy.
3. **Heart Rate Zone Compliance (20%)**: Time spent within the planned physiological HR zone.

### Life Happens FSM (Runner State)
A finite state machine tracking runner continuity:
- `ACTIVE`: On track with training program.
- `SLIPPED`: Missed 1 session; auto-rebalancing engaged within the week.
- `MISSED_CRITICAL`: Missed Tier 1 anchor workout; recalibrating weekly structure.
- `DELOAD`: Entering scheduled recovery or post-illness ramp-up.
- `INJURED`: Program suspended; active rehab mode.
