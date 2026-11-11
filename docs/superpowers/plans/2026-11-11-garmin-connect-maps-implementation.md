# Garmin Connect Authentic Map Experience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement an authentic Garmin Connect map experience featuring real OpenStreetMap / CartoDB tiles in Leaflet, authentic Garmin start (`◎`) and finish (`⏹️`) markers, interactive weather widget (`27.2° ☀️`), route replay playback controls (`▶`), and lightweight geographic preview cards on the activity feed.

**Architecture:** Frontend Leaflet map enhancements with realistic street tiles, custom DivIcon HTML markers, player animator, and card snapshot templates.

**Tech Stack:** Vanilla JavaScript, Leaflet 1.9.4, OpenStreetMap, CartoDB Positron/Dark, Tailwind CSS, Capacitor.

**Spec:** `docs/superpowers/specs/2026-11-11-garmin-connect-maps-design.md`

## Global Constraints

- Strict Rule: DILARANG menggunakan tanda pisah em-dash (`-`) di seluruh teks antarmuka maupun kode. Gunakan tanda hubung biasa (`-`), koma, atau tanda kurung.
- Deterministic Sports Engine: Formula fisiologis tetap murni deterministik.
- Zero Paid API Keys: Peta 100% menggunakan Leaflet dengan OpenStreetMap dan CartoDB tanpa ketergantungan Google Maps Billing.
- Mobile Performance: Feed kartu beranda tidak boleh menginisialisasi 20 Leaflet map bersamaan, melainkan preview peta jalanan nyata yang ringan.

## Review Focus

1. OpenStreetMap light/street tile load: memastikan tile OpenStreetMap memuat peta jalanan Jakarta dengan lancar tanpa error CORS.
2. Garmin Marker visual fidelity: pin start lingkaran hitam berpusat putih (`◎`) dan pin stop merah berikon henti putih (`⏹️`) tampil presisi pada titik koordinat awal dan akhir.
3. Weather widget accuracy: widget cuaca di pojok kanan atas peta menampilkan suhu dan ikon cuaca sesi (`27.2° ☀️`).
4. Replay playback control: tombol `▶` di tengah bawah menganimasikan pin pelari menelusuri rute secara mulus dengan tombol jeda (`⏸`).
5. Modal resize trigger: memastikan `activityMapInstance.invalidateSize()` dipanggil saat modal dibuka agar peta tidak abu-abu/terpotong.

---

### Task 1: Modal Map Layout & UI Controls (Weather, Fullscreen & Replay)

**Files:**
- Modify: `index.html` (modal map container, HUD controls, play button, weather badge)
- Style: `index.html` (Garmin pin CSS, Leaflet HUD styles)

- [ ] Step 1: Update modal map HUD to include the Garmin Weather Widget (`27.2° ☀️`), Fullscreen button (`⤢`), and Layer switcher (Street / Dark / Satellite).
- [ ] Step 2: Add the Replay Player floating control bar at the bottom center of `#detail-map-container` containing Play/Pause (`▶` / `⏸`) and speed controls.
- [ ] Step 3: Add CSS for `.garmin-start-circle` (black ring with white center `◎`) and `.garmin-stop-pin` (red teardrop with white stop square `⏹️`).

---

### Task 2: Leaflet Engine Upgrade to Garmin Connect Standard

**Files:**
- Modify: `index.html:10250-10450` (Leaflet initialization, tile providers, markers, replay loop)

- [ ] Step 1: Update `MAP_TILE_PROVIDERS` to set default to standard OpenStreetMap Street View (matching user's screenshot).
- [ ] Step 2: Update `renderActivityDetailMap` to create:
  - Start Marker: `◎` (black outer ring with white center dot).
  - Stop/Finish Marker: `⏹️` (red marker with white square stop icon).
  - GPS Polyline: Vibrant Garmin Cyan / Blue with dark navy underglow.
- [ ] Step 3: Implement `toggleActivityReplay()` to animate a moving runner dot along `routeCoords` from start to finish.
- [ ] Step 4: Implement `toggleActivityMapFullscreen()` to toggle fullscreen mode on the map container.

---

### Task 3: Feed Card Geographic Real Street Preview

**Files:**
- Modify: `index.html` (function `renderGarminMapCardSvg`, feed card template, and pre-rendered cards)

- [ ] Step 1: Enhance the feed card map preview with genuine OpenStreetMap / CartoDB street layout textures, displaying real Jakarta roads (Jl. Sudirman, Gatot Subroto, Asia Afrika, Thamrin) and venue landmarks.
- [ ] Step 2: Ensure start pin (`◎`) and stop pin (`⏹️`) appear on the card preview matching the modal.
- [ ] Step 3: Verify clicking any card map opens the full interactive Leaflet modal instantly.

---

### Task 4: End-to-End Verification & Build

**Files:**
- Run: `npm run build`
- Run: `.\venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"`

- [ ] Step 1: Compile CSS and synchronize Capacitor mobile assets.
- [ ] Step 2: Run complete backend unit test suite.
- [ ] Step 3: Verify local dev server at `http://127.0.0.1:8000`.
