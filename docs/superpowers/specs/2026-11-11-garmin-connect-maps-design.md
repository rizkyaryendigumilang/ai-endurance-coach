# Spesifikasi Desain: Tampilan Peta Sesi Olahraga Otentik Garmin Connect

- **Tanggal:** 2026-11-11
- **Topik:** Integrasi Tampilan Peta Geografis Nyata Sesuai Garmin Connect (OpenStreetMap / CartoDB via Leaflet)
- **Status:** Menunggu Persetujuan Pengguna (*Pending Approval*)

---

## 1. Latar Belakang & Tujuan (Intent & Why)

Pengguna melampirkan tangkapan layar antarmuka Garmin Connect asli (`media_1794373412646_f2eae3f5.jpg`) yang menampilkan peta lari di wilayah Jakarta. Pengguna menegaskan bahwa kebutuhan utama bukan sekadar modifikasi warna garis SVG, melainkan **kesamaan dengan Garmin Connect yang menampilkan peta jalanan nyata (*real street map*)**, lengkap dengan nama jalan, wilayah Jakarta, pin start/finish otentik Garmin, kontrol peta, widget cuaca, dan tombol replay pergerakan rute.

---

## 2. Sasaran & Batasan (Goals, Non-Goals, Anti-Goals)

### Sasaran (Goals):
1. **Peta Interaktif Penuh di Modal Detail Sesi:**
   - Menggunakan pustaka Leaflet yang sudah terpasang dengan layer OpenStreetMap / CartoDB (tanpa API key).
   - Menampilkan peta jalanan kota Jakarta (nama jalan, gedung, kawasan seperti Gelora Bung Karno Main Stadium, SCBD, Sudirman, Menteng, Monas).
   - **Pin Start Garmin Otentik:** Lingkaran hitam dengan titik putih di tengah (`◎`).
   - **Pin Finish/Stop Garmin Otentik:** Pin merah dengan kotak putih berhenti di tengah (`⏹️`).
   - **Widget Cuaca Sesi:** Menampilkan temperatur cuaca saat sesi berlangsung di pojok kanan atas peta (contoh: `27.2° ☀️`).
   - **Kontrol Peta:** Tombol Zoom (`+` / `-`), Layer switcher (Street / Dark / Satelit), dan tombol Layar Penuh (*Fullscreen* `⤢`).
   - **Fitur Replay Rute (`▶`):** Tombol pemutar di bagian bawah untuk menganimasikan jejak langkah pelari dari start ke finish secara interaktif.
2. **Tampilan Kartu Feed Beranda (Standar Garmin):**
   - Kartu feed aktivitas di beranda menampilkan preview peta jalanan nyata yang ringan, sehingga scrolling 20 sesi tetap lancar (60 FPS) di perangkat seluler maupun desktop.
   - Mengarahkan pengguna langsung ke modal peta interaktif lengkap saat kartu peta ditekan.

### Bukan Sasaran (Non-Goals):
- Tidak menggunakan Google Maps JavaScript API berbayar agar aplikasi tetap bebas biaya (*zero billing dependency*) dan mandiri.

### Hal yang Dihindari (Anti-Goals):
- Jangan menginisialisasi 20 instance peta Leaflet aktif secara bersamaan di dalam satu feed beranda, karena akan membebani RAM dan menurunkan performa render pada ponsel.

---

## 3. Pendekatan yang Dipertimbangkan & Dipilih

| Pendekatan | Kelebihan | Kekurangan | Status |
| :--- | :--- | :--- | :--- |
| **Pendekatan 1: Google Maps API** | Watermark persis seperti Google Maps. | Butuh Google Cloud billing dan API Key berbayar yang rawan kuota habis. | Ditolak |
| **Pendekatan 2: 20 Leaflet Aktif di Feed Beranda** | Interaktif langsung di beranda. | Sangat berat di mobile browser, boros memori (20 peta aktif sekaligus). | Ditolak |
| **Pendekatan 3: Leaflet OpenStreetMap + Modal Lengkap Garmin (Dipilih)** | 100% gratis, cepat, tanpa API Key, performa 60 FPS, fitur 100% lengkap sesuai screenshot pengguna. | Feed beranda menggunakan preview peta yang dioptimalkan, interaksi penuh di modal. | **DIPILIH (Opsi 1A & 2A)** |

---

## 4. Rincian Desain Antarmuka (UI/UX)

### A. Modal Detail Aktivitas (Peta Interaktif Penuh)
1. **Header Peta:**
   - Tombol Zoom (`+` / `-`) dan Pemilih Layer di pojok kiri atas.
   - Widget Cuaca: `27.2° ☀️` (diambil dari data cuaca sesi / Open-Meteo) di pojok kanan atas.
   - Tombol Layar Penuh (*Fullscreen* `⤢`).
2. **Kanvas Peta (Leaflet):**
   - Layer Default: OpenStreetMap / CartoDB Street View terang (sesuai screenshot pengguna) dengan opsi ganti ke Satelit atau Dark.
   - Lintasan GPS: Polyline rute jalanan Jakarta dengan warna biru / cyan gradien Garmin.
   - Marker Start: DivIcon Leaflet lingkaran hitam dengan titik putih (`◎`).
   - Marker Finish: DivIcon Leaflet pin merah dengan kotak stop putih (`⏹️`).
3. **Bagian Bawah Peta:**
   - Tombol Pemutar Replay (`▶`) di tengah bawah untuk menjalankan animasi pelari menelusuri rute.
   - Skala jarak (contoh: `3 km / 2 mi`) di pojok kanan bawah.

### B. Kartu Feed Beranda (Cockpit)
- Kanvas peta preview jalanan nyata berdimensi ringkas dengan penanda rute, pin start/finish, dan label lokasi Jakarta (GBK Senayan, Sudirman, Monas).
- Klik kartu langsung membuka peta interaktif penuh di atas.

---

## 5. Rencana Pengujian & Verifikasi
1. Verifikasi render peta interaktif Leaflet di modal dengan marker start `◎` dan stop `⏹️`.
2. Verifikasi interaksi tombol zoom, layer switcher, tombol fullscreen, widget cuaca `27.2° ☀️`, dan tombol replay `▶`.
3. Jalankan suite pengujian unit backend Python (`test_*.py`).
4. Jalankan kompilasi aset frontend dan sinkronisasi Capacitor (`npm run build`).
