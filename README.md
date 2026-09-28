# Dashboard Proyeksi Curah Hujan

Dashboard web interaktif untuk menjelajahi data NetCDF hasil proyeksi curah hujan
(per variabel, skenario, periode, jenis Klimatologi/Tren, dan model).

## Struktur folder yang diharapkan

Sekarang mendukung **lebih dari satu kategori data** (misalnya curah hujan dan suhu)
sekaligus, dipilih lewat dropdown "Kategori" di dashboard.

```
proyeksi_curah_hujan/
  <VARIABEL>/              contoh: CDD, RX1DAY, SDII, dst
    historical/             skenario historis — otomatis masuk grup "Historical"
      <PERIODE>/            contoh: 1981_2010
        <JENIS>/             KLIMATOLOGI atau TREND
          <MODEL>_<JENIS>_<PERIODE>.nc
    future/                 skenario masa depan — otomatis masuk grup "Future (Proyeksi)"
      ssp245/
        <PERIODE>/          contoh: 2021_2050
          <JENIS>/
            <MODEL>_<JENIS>_<PERIODE>.nc
      ssp370/
        ...
      ssp585/
        ...

proyeksi_suhu/
  <VARIABEL>/               struktur sama persis seperti di atas
    historical/...
    future/ssp245|ssp370|ssp585/...
```

**Mengatur kategori & path:** default-nya dua kategori sudah otomatis dikenali —
"Curah Hujan" → folder `proyeksi_curah_hujan`, "Suhu" → folder `proyeksi_suhu`
(keduanya dicari relatif terhadap folder tempat `app.py` dijalankan). Kalau lokasi
atau jumlah kategorinya beda, override lewat environment variable `DATA_ROOTS`,
format `Label1:path1,Label2:path2`, misalnya:

```bash
DATA_ROOTS="Curah Hujan:/data/proyeksi_curah_hujan,Suhu:/data/proyeksi_suhu" PORT=5090 python app.py
```

**Catatan tentang skenario:** folder bernama mengandung kata "historical"
(case-insensitive) masuk ke grup **Historical**; folder "future" lalu berisi
sub-folder skenario (`ssp245`, `ssp370`, `ssp585`, atau nama lain apa pun) yang
otomatis masuk ke grup **Future (Proyeksi)** dan muncul di dropdown "Skenario
proyeksi". Struktur lama tanpa folder historical/future eksplisit
(`VARIABEL/SKENARIO/PERIODE/JENIS/MODEL.nc`) juga masih didukung sebagai fallback.

Setiap file `.nc` diasumsikan punya koordinat `lat`/`lon` (atau `latitude`/`longitude`)
dan satu data variable (misalnya `slope`, `climatology`, dsb — nama variabelnya
otomatis terdeteksi, tidak perlu sama di semua file).

## Cara menjalankan

1. Taruh folder `app.py`, `templates/`, `requirements.txt` ini di satu tempat,
   dan letakkan folder data `proyeksi_curah_hujan/` di sebelahnya (atau di mana saja,
   lalu set path lewat `DATA_DIR`).

   ```
   project/
     app.py
     requirements.txt
     templates/
       index.html
     proyeksi_curah_hujan/       <-- data Anda
       CDD/
         historical/
           1981_2010/
             KLIMATOLOGI/...
             TREND/...
   ```

2. Install dependensi:

   ```bash
   pip install -r requirements.txt
   ```

3. Jalankan (default port 5090, default DATA_DIR = "proyeksi_curah_hujan" relatif
   terhadap folder tempat `app.py` dijalankan):

   ```bash
   python app.py
   ```

   Atau kalau folder data ada di lokasi lain:

   ```bash
   DATA_DIR=/path/lengkap/ke/proyeksi_curah_hujan PORT=5090 python app.py
   ```

4. Buka browser ke: **http://localhost:5090**

## Cara kerja singkat

- Saat start, `app.py` men-scan seluruh struktur folder `DATA_DIR` dan membangun
  index (variabel → skenario → periode → jenis → model → path file).
- Endpoint `/api/options` mengembalikan seluruh index itu untuk mengisi dropdown
  bertingkat di frontend.
- Endpoint `/api/data?variabel=...&skenario=...&periode=...&jenis=...&model=...`
  membaca file `.nc` yang sesuai (dengan `xarray`, hasil dicache) dan mengembalikan
  `lat`, `lon`, `z` sebagai JSON.
- Frontend (`templates/index.html`) memakai Plotly untuk menggambar peta kontur,
  dan otomatis update saat pilihan dropdown berubah.

## Kalau nama folder/pola nama file Anda sedikit berbeda

- Kalau urutan foldernya bukan `VARIABEL/SKENARIO/PERIODE/JENIS`, sesuaikan
  fungsi `build_index()` di `app.py` (tinggal ubah urutan `for` loop-nya).
- Kalau nama file tidak mengikuti pola `MODEL_JENIS_PERIODE.nc`, regex di
  `build_index()` akan fallback memakai nama file (tanpa `.nc`) sebagai nama model
  — masih akan berjalan, hanya label modelnya mungkin kurang rapi.
- Kalau variabel koordinat bukan `lat`/`lon` atau `latitude`/`longitude`,
  sesuaikan bagian itu di fungsi `read_nc()`.

## Troubleshooting

- **"Tidak ada data ditemukan"**: cek apakah `DATA_DIR` sudah menunjuk ke folder
  yang benar (jalankan `python app.py` dan lihat log jumlah file `.nc` yang
  ditemukan saat startup).
- **Error saat baca file**: pastikan `netCDF4` sudah terinstall dengan benar
  (`pip install netCDF4`), dan file `.nc` tidak corrupt (`ncdump -h file.nc`).

## Mengatur skala warna per variabel & jenis data

Skala warna (rentang min/max dan palet) diatur lewat file **`color_scales.json`**,
terpisah dari kode. Formatnya:

```json
{
  "default": {
    "KLIMATOLOGI": { "min": null, "max": null, "palette": "viridis" },
    "TREND":       { "min": null, "max": null, "palette": "rdbu" }
  },
  "CDD": {
    "KLIMATOLOGI": { "min": 0,  "max": 60, "palette": "viridis" },
    "TREND":       { "min": -5, "max": 5,  "palette": "rdbu" }
  }
}
```

- Kunci di level atas (`CDD`, `RX1DAY`, dst) harus sama persis dengan nama folder
  **VARIABEL** di struktur data Anda.
- Di dalamnya, kunci `KLIMATOLOGI` / `TREND` harus sama dengan nama folder **JENIS**.
- `min`/`max`: batas nilai untuk pewarnaan. Isi `null` kalau ingin dihitung otomatis
  dari data (rentang simetris di sekitar 0, cocok untuk data yang bisa negatif seperti tren).
- `palette`: salah satu dari `rdbu`, `viridis`, `jet`.
- Kunci **`default`** dipakai sebagai fallback untuk variabel yang belum
  didaftarkan satu per satu — jadi tidak wajib mengisi semua variabel dari awal.

Tambah/ubah variabel kapan saja di `color_scales.json`, lalu **restart** `python
app.py` (file dibaca sekali saat startup). Lokasi file bisa dipindah lewat
environment variable:

```bash
COLOR_CONFIG=/path/ke/color_scales.json python app.py
```

Kalau `color_scales.json` tidak ditemukan, dashboard tetap jalan normal dan otomatis
memakai rentang warna dari data (perilaku sebelumnya).

Catatan: kalau user mengubah slider "Skala Warna" secara manual di dashboard,
nilai manual itu yang dipakai (menimpa config) sampai halaman di-refresh.
