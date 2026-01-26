# MatchaIn GC (Matcha Input Gak Culun)

Aplikasi otomatisasi untuk melakukan upload data Ground Check (GC) ke server BPS menggunakan kombinasi Selenium (untuk otentikasi) dan Requests (untuk pengiriman data cepat).

## Fitur Utama
- **Otomatisasi Login**: Login otomatis menggunakan akun SSO BPS.
- **Dukungan OTP**: Mendukung input OTP otomatis (TOTP) atau input manual jika diperlukan.
- **Penyimpanan Sesi (Caching)**: Menyimpan sesi login ke `session.json` agar tidak perlu login ulang setiap kali aplikasi dijalankan.
- **Batch Processing**: Memproses semua file Excel (.xlsx/.xls) yang ada di folder `input/`.
- **Validasi Data**: Memastikan data Excel valid sebelum dikirim.
- **Smart Retry**: Otomatis memperbarui token jika sesi habis tanpa menghentikan proses.
- **Backup Otomatis**: Membuat backup data ke folder `backup/` sebelum proses dimulai.
- **Logging Lengkap**: Mencatat semua aktivitas ke file `app.log` dan konsol.
- **Resume Capability**: Melewati data yang sudah berstatus 'berhasil'.
- **Custom User Agent**: Bisa dikonfigurasi melalui file `.env`.

## Persyaratan Sistem
- Python 3.8 atau lebih baru.
- Google Chrome terinstall.
- Koneksi Internet.

## Panduan Instalasi & Penggunaan (Untuk Pemula)

Ikuti langkah-langkah di bawah ini untuk menginstall dan menjalankan aplikasi di komputer Anda.

### Langkah 1: Install Python
Aplikasi ini membutuhkan Python versi 3.8 ke atas.
1.  Buka web resmi Python: [python.org/downloads](https://www.python.org/downloads/)
2.  Klik tombol **Download Python 3.x.x**.
3.  Jalankan file installer yang sudah didownload.
4.  **PENTING**: Pada jendela instalasi, centang kotak **"Add Python to PATH"** sebelum klik "Install Now".
    > [!IMPORTANT]
    > Jika Anda lupa mencentang "Add Python to PATH", aplikasi tidak akan bisa berjalan. Jika sudah terlanjur, silakan install ulang dan pastikan dicentang.

### Langkah 2: Download Project
Ada dua cara untuk mendownload project ini:
-   **Cara Mudah (Download ZIP)**:
    1. Klik tombol hijau **"Code"** di halaman GitHub ini.
    2. Pilih **"Download ZIP"**.
    3. Setelah selesai, Extract file ZIP tersebut ke folder pilihan Anda.
-   **Cara Git**:
    1. Buka terminal atau Command Prompt.
    2. Ketik perintah: `git clone https://github.com/muhshi/scriptmatcha.git`

### Langkah 3: Pengaturan File `.env`
File `.env` digunakan untuk menyimpan username dan password Anda.
1. Cari file bernama `.env.example`.
2. Klik kanan, lalu pilih **Rename (Ganti Nama)** menjadi `.env` (hapus akhiran `.example`).
3. Buka file `.env` tersebut menggunakan Notepad.
4. Isi bagian `BPS_USERNAME` dan `BPS_PASSWORD` dengan kredensial SSO BPS Anda.
5. Simpan file (Ctrl+S).

### Langkah 4: Instalasi Awal & Menjalankan Aplikasi
Aplikasi ini sudah dilengkapi dengan script otomatis untuk mempermudah Anda.

1.  Buka folder project yang sudah di-extract/clone.
2.  Cari file bernama **`install_and_run.bat`**.
3.  Double-click (klik dua kali) file tersebut.
4.  Jendela Command Prompt akan muncul dan otomatis:
    - Membuat Virtual Environment (wadah khusus library).
    - Mendownload library yang dibutuhkan (Requests, Selenium, dll).
    - Langsung menjalankan aplikasi.

### Penggunaan Selanjutnya
Setelah instalasi pertama selesai, di kemudian hari Anda cukup double-click file **`run.bat`** untuk menjalankan aplikasi dengan lebih cepat tanpa melakukan instalasi ulang.

---

## Persiapan Data Excel
Sebelum menjalankan aplikasi, pastikan data Anda sudah siap:
1.  Buka folder **`input/`**.
2.  Letakkan file Excel GC Anda di sana.
3.  Pastikan format kolom sesuai:
    - `perusahaan_id`, `latitude`, `longitude`, `hasilgc`, `edit_nama`, `edit_alamat`, `nama_usaha`, `alamat_usaha`.

## Aturan Validasi Data (PENTING!)
Agar proses lancar, pastikan data Excel memenuhi aturan berikut:

1. **hasilgc**: Harus `1` (Aktif), `3` (Tutup Sem.), `4` (Tutup Perm.), atau `99` (Tidak Ditemukan).
2. **Konsistensi Nama/Alamat**:
   - Jika `nama_usaha` diisi, `edit_nama` harus `1`. Jika kosong, `edit_nama` harus `0`.
   - Aturan sama berlaku untuk `alamat_usaha` dan `edit_alamat`.
3. **Status Skip**: 
   - Aplikasi akan otomatis melewati (skip) baris yang sudah bertatus **"berhasil"** atau **"sudah diground check oleh user lain"**.

## Troubleshooting
- **File Excel Terkunci**: Pastikan semua file Excel di folder `input/` **TERTUTUP** saat aplikasi berjalan.
- **Token Invalid**: Aplikasi akan mencoba login ulang otomatis. Jika gagal terus-menerus, cek koneksi internet atau kredensial di `.env`.
- **Log**: Cek file `app.log` untuk detail error.

---
*Daftar User Agent Android WebView bisa dilihat di revisi Git sebelumnya jika diperlukan.*
#### Daftar User Agent Android WebView (Referensi)
Anda bisa menggunakan salah satu dari daftar berikut:

**Android 11 – WebView berbasis Chrome 86**
`Mozilla/5.0 (Linux; Android 11; Pixel 4 XL Build/RQ3A.210705.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/86.0.4240.198 Mobile Safari/537.36`

**Android 10 – WebView berbasis Chrome 80**
`Mozilla/5.0 (Linux; Android 10; SM‑G975F Build/QP1A.190711.020; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/80.0.3987.162 Mobile Safari/537.36`

**Android 9 – WebView berbasis Chrome 69**
`Mozilla/5.0 (Linux; Android 9; Redmi Note 7 Build/PKQ1.180904.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/69.0.3497.100 Mobile Safari/537.36`

**Android 8 Oreo – WebView berbasis Chrome 66**
`Mozilla/5.0 (Linux; Android 8.1.0; Nexus 5X Build/OPM4.171019.021I; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/66.0.3359.158 Mobile Safari/537.36`

**Android 7 Nougat – WebView berbasis Chrome 51**
`Mozilla/5.0 (Linux; Android 7.1.1; Moto G (5) Build/NMF26F; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/51.0.2704.81 Mobile Safari/537.36`

**Android 6 Marshmallow – WebView berbasis Chrome 44**
`Mozilla/5.0 (Linux; Android 6.0; Nexus 6 Build/MRA58K; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/44.0.2403.119 Mobile Safari/537.36`

**Android 5 Lollipop – WebView berbasis Chrome 40**
`Mozilla/5.0 (Linux; Android 5.0; Nexus 5 Build/LRX21T; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/40.0.2214.89 Mobile Safari/537.36`

**Android 4.4 KitKat – WebView berbasis Chrome 30**
`Mozilla/5.0 (Linux; Android 4.4.4; Nexus 5 Build/KRT16S; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/30.0.1599.107 Mobile Safari/537.36`
