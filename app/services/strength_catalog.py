# -*- coding: utf-8 -*-
"""
Database & Katalog 24 Gerakan Inti Latihan Beban (Gym) Pelari Maraton Goalie.
Menerapkan 4 Pilar Gerakan Fisiologis:
1. Unilateral Lower Body (Keseimbangan Pelvis & Kekuatan Bilateral)
2. Soleus & Achilles Complex (Penyerapan Impak 6.5–8x Berat Badan)
3. Plyometrics & Elastic Recoil (Kekakuan Pegas Tendon / Running Economy)
4. Anti-Rotation & Pelvic Stability (Pencegahan Form Hancur KM 30+)

Semua gerakan terkunci secara deterministik dengan batasan 2–3 RIR (Repetitions in Reserve)
dan aturan jeda steril 48–72 jam sebelum Long Run serta cutoff H-10 sebelum Race Day.
"""

from typing import Dict, List, Optional

MARATHON_STRENGTH_CATALOG: List[Dict] = [
    # ══════════════════════════════════════════════════════════════════════
    # PILAR 1: UNILATERAL LOWER BODY (6 GERAKAN)
    # ══════════════════════════════════════════════════════════════════════
    {
        "id": "bulgarian_split_squat",
        "pillar": "unilateral_lower_body",
        "pillar_name": "Unilateral Lower Body",
        "name": "Bulgarian Split Squat",
        "target_muscles": "Quadriceps, Gluteus Medius, Adductors",
        "sets_reps": "3 set x 8-10 repetisi / sisi",
        "rir_rule": "2-3 RIR (Berhenti 2-3 repetisi sebelum failure)",
        "tempo": "3-1-1 (3 detik deselerasi turun, 1 detik tahan, 1 detik dorong)",
        "primary_adaptation": "Keseimbangan daya dorong bilateral; mencegah overstriding dan asimetri langkah.",
        "form_cues": [
            "Letakkan kaki belakang di bangku setinggi lutut.",
            "Condongkan dada sedikit ke depan (15 derajat) untuk memfokuskan beban pada gluteus.",
            "Jaga lutut depan sejajar dengan jari kaki kedua, jangan biarkan menekuk ke dalam (valgus)."
        ],
        "safety_buffer_rule": "Wajib selesai minimal 48 jam sebelum Long Run akhir pekan.",
        "svg_icon": "squat"
    },
    {
        "id": "deficit_reverse_lunge",
        "pillar": "unilateral_lower_body",
        "pillar_name": "Unilateral Lower Body",
        "name": "Deficit Reverse Lunge",
        "target_muscles": "Gluteus Maximus, Hamstring, Hip Extensors",
        "sets_reps": "3 set x 8-10 repetisi / sisi",
        "rir_rule": "2-3 RIR",
        "tempo": "2-1-1",
        "primary_adaptation": "Meningkatkan rentang gerak ekstensi panggul tanpa tekanan berlebih pada patella.",
        "form_cues": [
            "Berdiri di atas bumper plate setinggi 5-10 cm.",
            "Langkah kaki ke belakang secara terkontrol sampai lutut belakang menyentuh lantai.",
            "Tolak lantai dengan tumit kaki depan untuk kembali ke posisi berdiri."
        ],
        "safety_buffer_rule": "Aman dilakukan 48 jam sebelum sesi interval/tempo.",
        "svg_icon": "lunge"
    },
    {
        "id": "weighted_box_step_up",
        "pillar": "unilateral_lower_body",
        "pillar_name": "Unilateral Lower Body",
        "name": "Weighted Box Step-Up",
        "target_muscles": "Gluteus Medius, Quadriceps, Ankle Stabilizers",
        "sets_reps": "3 set x 8-10 repetisi / sisi",
        "rir_rule": "2-3 RIR",
        "tempo": "2-1-2",
        "primary_adaptation": "Simulasi langsung fase stance (dorongan satu kaki) saat mendaki tanjakan.",
        "form_cues": [
            "Gunakan box setinggi tulang kering sampai bawah lutut.",
            "Hindari mendorong dengan jari kaki belakang; biarkan kaki depan menanggung 100% beban.",
            "Kunci posisi panggul agar sejajar saat berdiri tegak di atas box."
        ],
        "safety_buffer_rule": "Sangat efektif disatukan di hari yang sama pasca interval pagi.",
        "svg_icon": "step"
    },
    {
        "id": "single_leg_rdl",
        "pillar": "unilateral_lower_body",
        "pillar_name": "Unilateral Lower Body",
        "name": "Single-Leg Romanian Deadlift (RDL)",
        "target_muscles": "Hamstring, Gluteus, Intrinsic Foot Muscles",
        "sets_reps": "3 set x 8-10 repetisi / sisi",
        "rir_rule": "2-3 RIR",
        "tempo": "3-1-1",
        "primary_adaptation": "Daya tahan rantai posterior dan stabilitas proprioseptif telapak kaki.",
        "form_cues": [
            "Engselkan pinggul ke belakang dengan punggung lurus netral.",
            "Kaki belakang lurus memanjang ke belakang sebagai penyeimbang seperti timbangan.",
            "Tekuk sedikit lutut kaki tumpu, rasakan regangan di hamstring sebelum kembali tegak."
        ],
        "safety_buffer_rule": "Minimal 72 jam sebelum Long Run jika menggunakan beban berat.",
        "svg_icon": "deadlift"
    },
    {
        "id": "curtsy_lunge",
        "pillar": "unilateral_lower_body",
        "pillar_name": "Unilateral Lower Body",
        "name": "Curtsy Lunge",
        "target_muscles": "Gluteus Medius & Minimus, Tensor Fasciae Latae",
        "sets_reps": "3 set x 10 repetisi / sisi",
        "rir_rule": "2-3 RIR",
        "tempo": "2-1-1",
        "primary_adaptation": "Mencegah Iliotibial Band Syndrome (ITBS) dan drop panggul (Trendelenburg sign).",
        "form_cues": [
            "Langkahkan satu kaki menyilang diagonal ke belakang kaki tumpu.",
            "Pertahankan dada dan pinggul tetap menghadap lurus ke depan.",
            "Turunkan badan secara terkontrol sampai lutut belakang hampir menyentuh lantai."
        ],
        "safety_buffer_rule": "Gunakan beban ringan untuk menjaga kesehatan sendi panggul.",
        "svg_icon": "lunge"
    },
    {
        "id": "skater_squat",
        "pillar": "unilateral_lower_body",
        "pillar_name": "Unilateral Lower Body",
        "name": "Skater Squat (Supported)",
        "target_muscles": "Quadriceps, Glutes, Core Bracing",
        "sets_reps": "3 set x 6-8 repetisi / sisi",
        "rir_rule": "2 RIR",
        "tempo": "3-1-1",
        "primary_adaptation": "Kekuatan satu kaki tanpa kompresi spinal tulang belakang.",
        "form_cues": [
            "Angkat satu kaki ke belakang dengan lutut tertekuk 90 derajat.",
            "Turunkan tubuh dengan menekuk lutut depan sampai lutut belakang menyentuh matras busa.",
            "Dada tegak condong ke depan untuk mengimbangi titik gravitasi."
        ],
        "safety_buffer_rule": "Bisa menggunakan pegangan suspension strap jika keseimbangan masih labil.",
        "svg_icon": "squat"
    },

    # ══════════════════════════════════════════════════════════════════════
    # PILAR 2: SOLEUS & ACHILLES COMPLEX (6 GERAKAN)
    # ══════════════════════════════════════════════════════════════════════
    {
        "id": "seated_bent_knee_calf_raise",
        "pillar": "soleus_achilles_complex",
        "pillar_name": "Soleus & Achilles Complex",
        "name": "Seated Bent-Knee Calf Raise (90°)",
        "target_muscles": "Soleus Muscle (Otot Betis Dalam)",
        "sets_reps": "4 set x 12-15 repetisi (Beban Berat)",
        "rir_rule": "2 RIR",
        "tempo": "3-1-2 (Tahan puncak 1 detik, deselerasi eksentrik 3 detik)",
        "primary_adaptation": "Peredam impak 6.5–8x berat badan saat kaki mendarat; pelindung utama tendon Achilles.",
        "form_cues": [
            "Lutut ditekuk tepat 90 derajat untuk menginaktivasi gastrocnemius dan memaksimalkan soleus.",
            "Letakkan bantalan beban tepat di atas lutut.",
            "Turunkan tumit sedalam mungkin untuk mendapatkan regangan fasia plantar penuh."
        ],
        "safety_buffer_rule": "Kunci vital maraton: Soleus adalah otot ketahanan terbesar di tungkai bawah.",
        "svg_icon": "calf"
    },
    {
        "id": "standing_eccentric_heel_drop",
        "pillar": "soleus_achilles_complex",
        "pillar_name": "Soleus & Achilles Complex",
        "name": "Standing Eccentric Heel Drop",
        "target_muscles": "Gastrocnemius, Achilles Tendon",
        "sets_reps": "3 set x 12 repetisi / sisi",
        "rir_rule": "2-3 RIR",
        "tempo": "4-1-1 (Fase turun 4 detik sangat lambat)",
        "primary_adaptation": "Protokol Alfredson: Rekonstruksi arsitektur kolagen tendon Achilles.",
        "form_cues": [
            "Berdiri dengan bola kaki di tepi anak tangga atau balok kayu.",
            "Dorong ke atas dengan kedua kaki, lalu angkat satu kaki.",
            "Turunkan tumit satu kaki secara lambat selama 4 detik penuh di bawah level tangga."
        ],
        "safety_buffer_rule": "Lakukan setiap minggu untuk pencegahan tendinopati kronis.",
        "svg_icon": "calf"
    },
    {
        "id": "tibialis_anterior_wall_raise",
        "pillar": "soleus_achilles_complex",
        "pillar_name": "Soleus & Achilles Complex",
        "name": "Tibialis Anterior Wall Raise",
        "target_muscles": "Tibialis Anterior (Tulang Kering Depan)",
        "sets_reps": "3 set x 15-20 repetisi",
        "rir_rule": "2 RIR",
        "tempo": "2-1-1",
        "primary_adaptation": "Pencegahan cedera shin splints dan peningkatan kekuatan dorsofleksi pergelangan.",
        "form_cues": [
            "Sandarkan punggung di dinding dengan kaki berjarak 45 cm ke depan.",
            "Angkat jari dan telapak kaki setinggi mungkin ke arah tulang kering dengan tumit menempel lantai.",
            "Tahan 1 detik di puncak kontraksi sebelum menurunkan kaki kembali."
        ],
        "safety_buffer_rule": "Dapat dilakukan kapan saja tanpa menimbulkan kelelahan sistem saraf.",
        "svg_icon": "foot"
    },
    {
        "id": "heavy_isometric_ankle_hold",
        "pillar": "soleus_achilles_complex",
        "pillar_name": "Soleus & Achilles Complex",
        "name": "Heavy Isometric Ankle Hold",
        "target_muscles": "Achilles Tendon, Soleus, Plantar Fascia",
        "sets_reps": "4 set x 30-45 detik tahan",
        "rir_rule": "Isometrik Sub-Maksimal (70-80% MVC)",
        "tempo": "Tahan Statis Tanpa Gerakan",
        "primary_adaptation": "Analgesia tendon: Menghilangkan rasa ngilu tendon dan memperkuat kekakuan pegas.",
        "form_cues": [
            "Gunakan mesin Smith atau dumbel berat di kedua tangan.",
            "Angkat tumit 2-3 cm dari lantai (posisi mid-range).",
            "Tahan posisi diam membatu selama 35-45 detik dengan pernapasan teratur."
        ],
        "safety_buffer_rule": "Sangat aman dilakukan bahkan pada fase Tapering menjelang lomba.",
        "svg_icon": "hold"
    },
    {
        "id": "double_bounce_pogo_hops",
        "pillar": "soleus_achilles_complex",
        "pillar_name": "Soleus & Achilles Complex",
        "name": "Double-Bounce Pogo Hops",
        "target_muscles": "Achilles Tendon Spring, Gastrocnemius",
        "sets_reps": "3 set x 20 detik",
        "rir_rule": "Berhenti saat kontak kaki mulai lambat / berat",
        "tempo": "Kontak Lantai Singkat (< 0.2 detik)",
        "primary_adaptation": "Mempersingkat Ground Contact Time (GCT) dan melatih elastisitas pegas kaki.",
        "form_cues": [
            "Lompat vertikal menggunakan pergelangan kaki, bukan dengan menekuk lutut.",
            "Bayangkan lantai adalah wajan panas, pantulkan kaki secepat mungkin.",
            "Jaga pergelangan kaki terkunci kokoh (stiff ankle)."
        ],
        "safety_buffer_rule": "Jangan lakukan jika tendon Achilles sedang mengalami peradangan akut.",
        "svg_icon": "hop"
    },
    {
        "id": "farmers_toe_walk",
        "pillar": "soleus_achilles_complex",
        "pillar_name": "Soleus & Achilles Complex",
        "name": "Farmer's Toe Walk",
        "target_muscles": "Plantar Flexors, Core, Grip",
        "sets_reps": "3 set x 30 meter",
        "rir_rule": "2-3 RIR",
        "tempo": "Jalan Stabil Berirama",
        "primary_adaptation": "Kekuatan daya tahan telapak kaki dan stabilitas lengkung kaki (foot arch).",
        "form_cues": [
            "Pegang sepasang dumbel sedang di samping tubuh.",
            "Jinjitkan kedua tumit setinggi mungkin dari lantai.",
            "Berjalan lurus dengan langkah pendek terkontrol tanpa membiarkan tumit menyentuh lantai."
        ],
        "safety_buffer_rule": "Pondasi terbaik untuk pelari yang sering mengalami kram telapak kaki di atas KM 30.",
        "svg_icon": "walk"
    },

    # ══════════════════════════════════════════════════════════════════════
    # PILAR 3: PLYOMETRICS & ELASTIC RECOIL (6 GERAKAN)
    # ══════════════════════════════════════════════════════════════════════
    {
        "id": "low_amplitude_ankle_hops",
        "pillar": "plyometrics_elastic_recoil",
        "pillar_name": "Plyometrics & Elastic Recoil",
        "name": "Low-Amplitude Ankle Hops",
        "target_muscles": "Tendon Stiffness, Lower Limb Elasticity",
        "sets_reps": "3 set x 15-20 loncatan",
        "rir_rule": "Reaktif Cepat (Bukan Kelelahan)",
        "tempo": "Reaktif < 0.18 detik",
        "primary_adaptation": "Meningkatkan Running Economy hingga 2-4% tanpa kenaikan konsumsi oksigen (VO2).",
        "form_cues": [
            "Ketinggian loncatan hanya 5-10 cm, fokus pada kekakuan pergelangan kaki.",
            "Jaga tubuh tetap tegak lurus dengan lengan berayun ritmis.",
            "Tangan santai, bahu rileks."
        ],
        "safety_buffer_rule": "Wajib dilakukan di atas permukaan rata yang menyerap impak (matras/tartan/rumput).",
        "svg_icon": "hop"
    },
    {
        "id": "lateral_bound_to_stick",
        "pillar": "plyometrics_elastic_recoil",
        "pillar_name": "Plyometrics & Elastic Recoil",
        "name": "Lateral Bound to Stick",
        "target_muscles": "Gluteus Medius, Ankle Ligaments, Deceleration",
        "sets_reps": "3 set x 6-8 loncatan / sisi",
        "rir_rule": "Fokus Stabilitas Bukan Kecepatan",
        "tempo": "Lompat cepat, tahan mendarat 2 detik",
        "primary_adaptation": "Melatih deselerasi frontal dan proteksi pergelangan kaki dari cedera terkilir.",
        "form_cues": [
            "Lompat ke samping secara eksplosif dari satu kaki.",
            "Mendarat dengan satu kaki lainnya dan tahan posisi diam membatu selama 2 detik penuh.",
            "Pastikan lutut tidak goyang ke dalam saat menyerap pendaratan."
        ],
        "safety_buffer_rule": "Sangat penting bagi pelari half/full marathon yang berlari di tikungan jalan raya.",
        "svg_icon": "bound"
    },
    {
        "id": "broad_jump_with_reset",
        "pillar": "plyometrics_elastic_recoil",
        "pillar_name": "Plyometrics & Elastic Recoil",
        "name": "Broad Jump with Soft Stick",
        "target_muscles": "Gluteus Maximus, Hamstring, Triple Extension",
        "sets_reps": "3 set x 5 loncatan (Reset setiap repetisi)",
        "rir_rule": "Eksplosif Maksimal 100% Usaha",
        "tempo": "1 loncatan per 5 detik istirahat",
        "primary_adaptation": "Rekrutmen serat otot cepat (Type IIa) untuk akselerasi finish sprint.",
        "form_cues": [
            "Ayunkan lengan ke belakang bersamaan dengan menekuk lutut.",
            "Lompat ke depan sejauh mungkin dengan ekstensi panggul penuh.",
            "Mendarat selembut mungkin seperti kucing menyerap beban ke tumit dan panggul."
        ],
        "safety_buffer_rule": "Hanya 5 repetisi per set untuk menghindari fatigue neuromuskular.",
        "svg_icon": "jump"
    },
    {
        "id": "depth_drop_to_vertical_spring",
        "pillar": "plyometrics_elastic_recoil",
        "pillar_name": "Plyometrics & Elastic Recoil",
        "name": "Depth Drop to Vertical Spring",
        "target_muscles": "Stretch-Shortening Cycle (SSC), Fascia Springs",
        "sets_reps": "3 set x 5 repetisi",
        "rir_rule": "Kualitas Kontak Cepat",
        "tempo": "Kontak Instan",
        "primary_adaptation": "Memaksimalkan siklus peregangan-pemendekan otot (SSC) untuk efisiensi energi.",
        "form_cues": [
            "Melangkah turun dari box setinggi 20-30 cm (jangan melompat dari atas box).",
            "Begitu telapak kaki menyentuh lantai, langsung memantul ke atas setinggi mungkin.",
            "Lengan diayun ke atas untuk membantu dorongan vertikal."
        ],
        "safety_buffer_rule": "Hentikan jika pelari merasa lutut lemas atau pendaratan berbunyi keras.",
        "svg_icon": "drop"
    },
    {
        "id": "single_leg_linear_hops",
        "pillar": "plyometrics_elastic_recoil",
        "pillar_name": "Plyometrics & Elastic Recoil",
        "name": "Single-Leg Linear Hops",
        "target_muscles": "Unilateral Tendon Stiffness, Plantar Balance",
        "sets_reps": "3 set x 8 loncatan / kaki",
        "rir_rule": "2 RIR",
        "tempo": "Ritme Konstan",
        "primary_adaptation": "Menyamakan elastisitas pegas kaki kiri dan kanan agar langkah lari simetris.",
        "form_cues": [
            "Lompat maju perlahan dengan satu kaki sejauh 30-50 cm per lompatan.",
            "Pertahankan torso tegak lurus dan ayunkan lengan berlawanan.",
            "Jangan biarkan tumit menghempas keras ke lantai."
        ],
        "safety_buffer_rule": "Wajib dihentikan jika ada rasa nyeri tajam di tulang kering.",
        "svg_icon": "hop"
    },
    {
        "id": "quick_feet_ladder_in_out",
        "pillar": "plyometrics_elastic_recoil",
        "pillar_name": "Plyometrics & Elastic Recoil",
        "name": "Quick-Feet Ladder In-and-Out",
        "target_muscles": "Neuromuscular Cadence, Agility",
        "sets_reps": "3 set x 15 detik",
        "rir_rule": "Kecepatan Kaki Maksimal",
        "tempo": "Cadence Cepat (> 190 langkah/menit)",
        "primary_adaptation": "Membiasakan otak dan saraf kaki untuk berputar cepat pada cadence tinggi 175-185 spm.",
        "form_cues": [
            "Gunakan agility ladder atau garis ubin lantai.",
            "Gerakkan kaki masuk-keluar secepat mungkin dengan jari kaki rileks.",
            "Bahu dan rahang tetap santai tanpa menahan napas."
        ],
        "safety_buffer_rule": "Dapat dijadikan pemanasan dinamis sebelum latihan lari interval.",
        "svg_icon": "ladder"
    },

    # ══════════════════════════════════════════════════════════════════════
    # PILAR 4: ANTI-ROTATION & PELVIC STABILITY (6 GERAKAN)
    # ══════════════════════════════════════════════════════════════════════
    {
        "id": "banded_pallof_press",
        "pillar": "anti_rotation_pelvic_stability",
        "pillar_name": "Anti-Rotation & Pelvic Stability",
        "name": "Banded Pallof Press with Overhead Raise",
        "target_muscles": "Transverse Abdominis, Internal/External Obliques",
        "sets_reps": "3 set x 10-12 repetisi / sisi",
        "rir_rule": "2-3 RIR",
        "tempo": "2-1-2 (Tahan di depan dada 1 detik)",
        "primary_adaptation": "Menahan torsi rotasi torso saat lelah di KM 32+, menjaga efisiensi ayunan lengan.",
        "form_cues": [
            "Kaitkan resistance band pada tiang setinggi dada.",
            "Dorong tangan lurus ke depan melawan tarikan band ke samping.",
            "Angkat tangan ke atas kepala tanpa melengkungkan punggung bawah, lalu kembali ke dada."
        ],
        "safety_buffer_rule": "Latihan anti-rotasi terbaik yang tidak membebani bantalan tulang belakang.",
        "svg_icon": "core"
    },
    {
        "id": "copenhagen_adductor_plank",
        "pillar": "anti_rotation_pelvic_stability",
        "pillar_name": "Anti-Rotation & Pelvic Stability",
        "name": "Copenhagen Adductor Plank",
        "target_muscles": "Adductor Longus/Magnus, Lateral Core",
        "sets_reps": "3 set x 20-30 detik tahan / sisi",
        "rir_rule": "Isometrik Terkontrol",
        "tempo": "Tahan Statis",
        "primary_adaptation": "Mengunci stabilitas panggul dalam dan mencegah cedera selangkangan & lutut pelari.",
        "form_cues": [
            "Posisikan tubuh miring seperti side plank.",
            "Letakkan kaki atas di atas bangku, kaki bawah menggantung bebas atau menyentuh lantai.",
            "Angkat pinggul sehingga tubuh membentuk satu garis lurus kokoh."
        ],
        "safety_buffer_rule": "Mulai dengan tuas pendek (lutut di bangku) sebelum maju ke tuas panjang (pergelangan di bangku).",
        "svg_icon": "plank"
    },
    {
        "id": "banded_bird_dog",
        "pillar": "anti_rotation_pelvic_stability",
        "pillar_name": "Anti-Rotation & Pelvic Stability",
        "name": "Banded Bird Dog",
        "target_muscles": "Multifidus, Erector Spinae, Gluteus Maximus",
        "sets_reps": "3 set x 10 repetisi / sisi",
        "rir_rule": "2-3 RIR",
        "tempo": "3-2-2 (Tahan puncak 2 detik)",
        "primary_adaptation": "Sinkronisasi diagonal ekstremitas atas dan bawah persis mekanika langkah lari maraton.",
        "form_cues": [
            "Posisi merangkak dengan band melingkar di telapak kaki dan tangan.",
            "Panjangkan tangan kanan ke depan dan kaki kiri ke belakang secara bersamaan.",
            "Kunci perut agar punggung tidak melengkung atau berputar miring."
        ],
        "safety_buffer_rule": "Sangat dianjurkan bagi pelari dengan riwayat nyeri pinggang bawah (LBP).",
        "svg_icon": "core"
    },
    {
        "id": "suitcase_farmers_carry",
        "pillar": "anti_rotation_pelvic_stability",
        "pillar_name": "Anti-Rotation & Pelvic Stability",
        "name": "Suitcase Farmer's Carry (One-Sided)",
        "target_muscles": "Quadratus Lumborum, Obliques, Scapular Retractors",
        "sets_reps": "3 set x 40 meter / sisi",
        "rir_rule": "2-3 RIR",
        "tempo": "Langkah Lambat Stabil",
        "primary_adaptation": "Menahan kemiringan lateral panggul saat fase unweighting langkah lari.",
        "form_cues": [
            "Pegang satu dumbel/kettlebell berat hanya di satu sisi tangan (seperti membawa koper).",
            "Jaga bahu dan pinggul tetap sejajar horizontal sempurna, jangan condong ke sisi yang memegang beban.",
            "Berjalan lurus dengan langkah terkontrol dan pernapasan stabil."
        ],
        "safety_buffer_rule": "Lakukan di akhir sesi strength setelah gerakan unilateral selesai.",
        "svg_icon": "walk"
    },
    {
        "id": "deadbug_with_lumbar_imprint",
        "pillar": "anti_rotation_pelvic_stability",
        "pillar_name": "Anti-Rotation & Pelvic Stability",
        "name": "Deadbug with Lumbar Imprint",
        "target_muscles": "Rectus Abdominis, Deep Psoas, Diaphragm",
        "sets_reps": "3 set x 12 repetisi silang",
        "rir_rule": "2-3 RIR",
        "tempo": "3-1-2",
        "primary_adaptation": "Menghilangkan anterior pelvic tilt yang memicu kelelahan hamstring di akhir lomba.",
        "form_cues": [
            "Berbaring terlentang dengan tangan tegak dan lutut tertekuk 90 derajat.",
            "Tekan punggung bawah menempel rapat ke lantai tanpa ada celah udara.",
            "Turunkan tangan kanan dan kaki kiri secara perlahan sambil menghembuskan napas penuh."
        ],
        "safety_buffer_rule": "Gerakan dasar wajib sebelum memulai program maraton intensitas tinggi.",
        "svg_icon": "core"
    },
    {
        "id": "half_kneeling_cable_chop",
        "pillar": "anti_rotation_pelvic_stability",
        "pillar_name": "Anti-Rotation & Pelvic Stability",
        "name": "Half-Kneeling Cable / Band Chop",
        "target_muscles": "Rotary Obliques, Glute Tensors, Upper Back",
        "sets_reps": "3 set x 10 repetisi / sisi",
        "rir_rule": "2-3 RIR",
        "tempo": "2-1-2",
        "primary_adaptation": "Mentransfer tenaga kinetik dari panggul bawah ke ayunan torso atas secara hemat energi.",
        "form_cues": [
            "Berlutut satu kaki (kaki luar di depan, kaki dalam di lantai).",
            "Tarik band/kabel dari sudut tinggi diagonal melintasi tubuh ke pinggul bawah berlawanan.",
            "Pertahankan pinggul diam membatu; hanya torso atas dan pundak yang berputar."
        ],
        "safety_buffer_rule": "Hentikan jika merasakan kompresi berlebih pada tulang belikat.",
        "svg_icon": "core"
    }
]


class StrengthEngine:
    """
    Mesin Rekomendasi Latihan Beban Spesifik Maraton Goalie.
    Mengatur seleksi gerakan, aturan jeda concurrent training, dan cutoff H-10 lomba.
    """

    @staticmethod
    def get_catalog() -> List[Dict]:
        """Mengambil seluruh 24 katalog gerakan inti maraton."""
        return MARATHON_STRENGTH_CATALOG

    @staticmethod
    def get_exercises_by_pillar(pillar_key: str) -> List[Dict]:
        """Menyaring latihan berdasarkan salah satu dari 4 pilar."""
        return [ex for ex in MARATHON_STRENGTH_CATALOG if ex["pillar"] == pillar_key]

    @staticmethod
    def get_weekly_strength_session(week_number: int, days_to_race: int = 120) -> Dict:
        """
        Menghasilkan rekomendasi 2 sesi gym mingguan (Rabu & Jumat) dengan aturan:
        - 48-72 jam buffer sebelum Long Run.
        - Cutoff H-10 sebelum Race Day: hapus beban berat, ganti dengan mobilitas & isometrik ringan.
        """
        is_taper_cutoff = days_to_race <= 10
        is_late_taper = 10 < days_to_race <= 21

        if is_taper_cutoff:
            return {
                "status": "RACE_DAY_CUTOFF_ACTIVE",
                "message": "Cutoff H-10 Aktif: Hapus semua latihan angkat beban kaki demi menjaga glikogen penuh & otot segar.",
                "sessions": [
                    {
                        "day": "Rabu",
                        "title": "Taper Mobility & Light Isometric Ankle Hold",
                        "duration_min": 25,
                        "exercises": [
                            StrengthEngine.get_exercise_by_id("heavy_isometric_ankle_hold"),
                            StrengthEngine.get_exercise_by_id("tibialis_anterior_wall_raise"),
                            StrengthEngine.get_exercise_by_id("deadbug_with_lumbar_imprint")
                        ]
                    },
                    {
                        "day": "Jumat",
                        "title": "Shakeout Foam Rolling & Dynamic Stretches",
                        "duration_min": 20,
                        "exercises": [
                            StrengthEngine.get_exercise_by_id("banded_pallof_press")
                        ]
                    }
                ]
            }

        # Regular periodization: Wednesday (Unilateral + Soleus) & Friday (Core Anti-Rotation + Achilles Plyo)
        wed_ex = [
            StrengthEngine.get_exercise_by_id("bulgarian_split_squat"),
            StrengthEngine.get_exercise_by_id("weighted_box_step_up"),
            StrengthEngine.get_exercise_by_id("seated_bent_knee_calf_raise"),
            StrengthEngine.get_exercise_by_id("tibialis_anterior_wall_raise")
        ]

        fri_ex = [
            StrengthEngine.get_exercise_by_id("copenhagen_adductor_plank"),
            StrengthEngine.get_exercise_by_id("banded_pallof_press"),
            StrengthEngine.get_exercise_by_id("heavy_isometric_ankle_hold"),
            StrengthEngine.get_exercise_by_id("double_bounce_pogo_hops")
        ]

        return {
            "status": "NORMAL_PERIODIZATION",
            "message": "Patuhi aturan 2-3 RIR dan jeda minimal 6 jam setelah lari pagi.",
            "concurrent_rules": {
                "keep_hard_days_hard": "Dahulukan Lari di pagi hari, Gym di sore/malam dengan jeda minimal 6 jam.",
                "long_run_buffer": "Zona steril 48-72 jam sebelum Long Run akhir pekan.",
                "rir_target": "2-3 RIR (Jangan pernah berlatih sampai failure mekanik)."
            },
            "sessions": [
                {
                    "day": "Rabu 12:00-13:00 WIB",
                    "title": "Pilar 1 & 2: Pelvic Stance & Soleus Resilience",
                    "duration_min": 45,
                    "exercises": [e for e in wed_ex if e]
                },
                {
                    "day": "Jumat 12:00-13:00 WIB",
                    "title": "Pilar 3 & 4: Tendon Elasticity & Anti-Rotation Core",
                    "duration_min": 45,
                    "exercises": [e for e in fri_ex if e]
                }
            ]
        }

    @staticmethod
    def get_exercise_by_id(exercise_id: str) -> Optional[Dict]:
        """Mencari gerakan berdasarkan ID unik."""
        for ex in MARATHON_STRENGTH_CATALOG:
            if ex["id"] == exercise_id:
                return ex
        return None
