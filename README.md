# Finance Tracker Bot (Telegram)

Proyek pribadi untuk mencatat pemasukan dan pengeluaran harian dengan cepat, mudah, dan praktis langsung lewat Telegram.

---

## Tentang Proyek Ini

Proyek ini saya buat untuk kebutuhan pribadi dalam mengelola arus kas harian tanpa ribet. Sering kali aplikasi keuangan di ponsel terlalu lambat dibuka, penuh iklan, atau formulirnya terlalu panjang saat kita hanya ingin mencatat hal sederhana (seperti beli kopi atau bayar parkir). 

Dengan bot Telegram ini, pencatatan transaksi bisa selesai dalam beberapa detik:
- Cukup ketik format kilat seperti `- 25k makan siang` saat sedang terburu-buru.
- Atau gunakan wizard tombol interaktif saat ingin memilih kategori secara rapi.
- Semua data tersimpan aman secara lokal di database SQLite pribadi tanpa bergantung pada layanan cloud berbayar pihak ketiga.

---

## Fitur Utama

- ⚡ **Quick-Add (Pencatatan Instan)**  
  Tulis pengeluaran atau pemasukan langsung di kolom chat:
  - `- 25k makan siang` *(Pengeluaran Rp 25.000 kategori Makanan)*
  - `+ 5jt gaji bulanan` *(Pemasukan Rp 5.000.000 kategori Gaji)*
  - `keluar 50rb bensin motor`
- 🧙 **Interactive Menu & Wizard (`/start`, `/add`)**  
  Panduan bertahap menggunakan tombol inline: pilih tipe $\rightarrow$ kategori $\rightarrow$ nominal $\rightarrow$ catatan opsional $\rightarrow$ konfirmasi.
- 🇮🇩 **Parsing Mata Uang Rupiah Alami**  
  Mendukung format penulisan umum Indonesia: `50k`, `50rb`, `1.5jt`, `50.000`, hingga angka polos `50000`.
- ✏️ **Edit & Hapus Transaksi (`/edit`, `/history`)**  
  Manusia wajar salah ketik. Tersedia tombol *Undo* langsung setelah menyimpan, serta menu `/edit` untuk mengubah nominal, kategori, atau catatan transaksi yang sudah tersimpan.
- 📊 **Laporan Visual (`/report`)**  
  Ringkasan pengeluaran bulanan dan mingguan lengkap dengan progress bar visual (`[██████░░░░] 60%`) dan rincian per kategori.
- 📤 **Export ke CSV / Excel (`/export`)**  
  Unduh seluruh riwayat transaksi dalam format CSV (UTF-8 with BOM) yang bisa langsung dibuka rapi di Microsoft Excel atau Google Sheets.
- 🏷 **Kategori Kustom (`/categories`)**  
  Tambah kategori baru sesuai kebutuhan atau kelola kategori yang sudah ada.
- 🔒 **Proteksi Akun Pribadi**  
  Tersedia setelan `ADMIN_CHAT_ID` agar bot hanya merespons akun Telegram pemiliknya saja.

---

## Tech Stack

- **Python 3.10+** (diuji pada Python 3.12)
- **aiogram 3.x** — Framework asinkron modern untuk Telegram Bot API
- **aiosqlite** — SQLite asinkron dengan WAL mode & foreign keys untuk performa cepat dan aman dari korupsi data
- **python-dotenv** — Manajemen konfigurasi dan token rahasia

---

## Panduan Menjalankan Sendiri

Jika Anda ingin menjalankan bot ini untuk keperluan pribadi Anda sendiri, ikuti langkah berikut:

### 1. Dapatkan Bot Token
1. Buka aplikasi Telegram, cari akun resmi `@BotFather`.
2. Kirim perintah `/newbot` dan ikuti instruksi hingga selesai.
3. Salin **HTTP API Token** yang diberikan.

### 2. Clone & Install Dependensi
```bash
git clone https://github.com/Diptaaaa/bot_telegram_pencatatan_keuangan.git
cd bot_telegram_pencatatan_keuangan

# Buat virtual environment
python -m venv venv

# Aktifkan virtual environment
venv\Scripts\activate      # Windows (PowerShell/CMD)
# source venv/bin/activate # Linux / macOS

# Install dependensi
pip install -r requirements.txt
```

### 3. Buat File Konfigurasi `.env`
Salin atau buat file `.env` di folder utama:
```env
BOT_TOKEN=masukkan_token_bot_anda_di_sini

# Opsional: Masukkan Chat ID Telegram Anda agar bot hanya merespons Anda.
# Jika dikosongkan, bot dapat dipakai siapa saja yang memulai chat.
ADMIN_CHAT_ID=123456789
```

### 4. Jalankan Bot
```bash
python bot.py
```
Buka bot Anda di Telegram dan ketik `/start` atau langsung coba ketik `- 20k kopi susu`.

### 5. Menjalankan Unit Test
Proyek ini dilengkapi pengujian unit otomatis untuk memastikan parser nominal rupiah dan logika database berjalan benar:
```bash
python test_finance.py
```

---

## Struktur File

```text
finance-bot/
├── bot.py                   # Entry point bot, router, FSM wizard & handler chat
├── db.py                    # Operasi database SQLite asinkron (aiosqlite)
├── keyboards.py             # Builder tombol inline keyboard Telegram
├── utils.py                 # Parser nominal rupiah, pembaca tanggal, export CSV
├── test_finance.py          # Unit test parser & alur transaksi
├── requirements.txt         # Daftar pustaka Python
├── .env.example             # Template variabel lingkungan
├── LICENSE                  # Lisensi proyek (MIT)
├── README.md                # Dokumentasi proyek
└── data/                    # Folder penyimpanan database SQLite (dibuat otomatis)
```

---

## Lisensi

Proyek ini dirilis di bawah lisensi [MIT](LICENSE). Silakan gunakan, pelajari, atau kembangkan sesuai kebutuhan pribadi Anda.
