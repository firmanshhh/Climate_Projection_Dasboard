"""
Dashboard interaktif untuk data proyeksi iklim (curah hujan, suhu, dst) dari NetCDF.

Struktur folder yang diharapkan per kategori, mis. proyeksi_curah_hujan/ atau proyeksi_suhu/:
  <ROOT>/
    <VARIABEL>/                       contoh: CDD, RX1DAY, TXX, dst
      historical/
        <PERIODE>/                     contoh: 1981_2010
          <JENIS>/                      KLIMATOLOGI atau TREND
            <MODEL>_<JENIS>_<PERIODE>.nc
      future/
        <SKENARIO>/                    contoh: ssp245, ssp370, ssp585
          <PERIODE>/                    contoh: 2021_2050
            <JENIS>/
              <MODEL>_<JENIS>_<PERIODE>.nc

Jalankan:
  pip install -r requirements.txt
  export DATA_ROOTS="Curah Hujan:proyeksi_curah_hujan,Suhu:proyeksi_suhu"   # opsional
  export COLOR_CONFIG=color_scales.json                                     # opsional
  python app.py
  # buka http://localhost:5090
"""

import os
import re
import json
import logging
from functools import lru_cache

import numpy as np
import xarray as xr
from flask import Flask, jsonify, request, render_template

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("dashboard")

# Root folder data. Bisa lebih dari satu kategori, mis. curah hujan & suhu.
# Format env var DATA_ROOTS: "Label1:path1,Label2:path2"
# Default: kategori "Curah Hujan" -> proyeksi_curah_hujan, "Suhu" -> proyeksi_suhu
DEFAULT_ROOTS = "Curah Hujan:proyeksi_curah_hujan,Suhu:proyeksi_suhu"
PORT = int(os.environ.get("PORT", 5090))

app = Flask(__name__)


def parse_data_roots():
    raw = os.environ.get("DATA_ROOTS", DEFAULT_ROOTS)
    roots = {}
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            label, path = part.split(":", 1)
        else:
            label, path = part, part
        roots[label.strip()] = path.strip()
    return roots


# Path ke file konfigurasi skala warna (bisa di-override lewat COLOR_CONFIG env var)
COLOR_CONFIG_PATH = os.environ.get("COLOR_CONFIG", "config_colors.json")
COLOR_CONFIG = {}


def load_color_config(path):
    """Baca file JSON konfigurasi skala warna. Aman kalau file tidak ada/rusak."""
    if not os.path.exists(path):
        log.warning("File konfigurasi skala warna '%s' tidak ditemukan, memakai auto-range default.", path)
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        cfg.pop("_readme", None)
        log.info("Konfigurasi skala warna dimuat dari '%s' (%d variabel).", path, len(cfg))
        return cfg
    except Exception as e:
        log.error("Gagal membaca konfigurasi skala warna '%s': %s", path, e)
        return {}


def get_color_scale(variabel, jenis):
    """Cari entri skala warna untuk variabel+jenis tertentu, fallback ke 'default'."""
    entry = COLOR_CONFIG.get(variabel) or COLOR_CONFIG.get(variabel.upper()) or {}
    scale = entry.get(jenis) or entry.get(jenis.upper())
    if scale is None:
        default_entry = COLOR_CONFIG.get("default", {})
        scale = default_entry.get(jenis) or default_entry.get(jenis.upper())
    return scale


def ensure_plotly_js():
    """Tulis static/plotly.min.js dari package python 'plotly' (offline, tanpa CDN)."""
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
    os.makedirs(static_dir, exist_ok=True)
    target = os.path.join(static_dir, "plotly.min.js")
    if os.path.exists(target) and os.path.getsize(target) > 100_000:
        return
    try:
        import plotly.offline as pyo
        with open(target, "w", encoding="utf-8") as f:
            f.write(pyo.get_plotlyjs())
        log.info("plotly.min.js berhasil di-generate ke %s", target)
    except Exception as e:
        log.error(
            "Gagal generate plotly.min.js secara otomatis (%s). "
            "Install package 'plotly' (pip install plotly) lalu jalankan ulang, "
            "atau taruh manual file plotly.min.js di folder static/.", e
        )

# INDEX kini berlapis kategori paling luar:
# INDEX = {
#   "<kategori>": {
#     "<variabel>": {
#       "<skenario>": {
#         "<periode>": {
#           "<jenis>": {
#             "<model>": "<path file .nc>"
#           }
#         }
#       }
#     }
#   }
# }
INDEX = {}


def build_index(root):
    """Scan struktur folder dan bangun index metadata -> path file.

    Mendukung dua pola struktur di bawah setiap VARIABEL:
      historical/PERIODE/JENIS/MODEL.nc
      future/SKENARIO/PERIODE/JENIS/MODEL.nc

    Hasil index selalu diratakan ke bentuk:
      variabel -> skenario -> periode -> jenis -> model -> path
    di mana untuk folder "historical", skenario diisi "historical",
    dan untuk folder "future", skenario diisi nama folder skenarionya
    (mis. ssp245, ssp370, ssp585).
    """
    index = {}
    if not os.path.isdir(root):
        log.warning("DATA_DIR '%s' tidak ditemukan. Jalankan dengan DATA_DIR yang benar.", root)
        return index

    pattern = re.compile(r"^(?P<model>.+?)_(?P<jenis>[A-Za-z0-9]+)_(?P<periode>\d{4}_\d{4})\.nc$")

    def add_file(variabel, skenario, periode, jenis, fname, full_path):
        m = pattern.match(fname)
        model = m.group("model") if m else fname.replace(".nc", "")
        periode_key = m.group("periode") if m else periode
        index.setdefault(variabel, {}) \
             .setdefault(skenario, {}) \
             .setdefault(periode_key, {}) \
             .setdefault(jenis, {})[model] = full_path

    def walk_periode_jenis_model(variabel, skenario, periode_root):
        """Dari level PERIODE ke bawah: PERIODE/JENIS/MODEL.nc"""
        if not os.path.isdir(periode_root):
            return
        for periode in sorted(os.listdir(periode_root)):
            per_path = os.path.join(periode_root, periode)
            if not os.path.isdir(per_path):
                continue
            for jenis in sorted(os.listdir(per_path)):
                jenis_path = os.path.join(per_path, jenis)
                if not os.path.isdir(jenis_path):
                    continue
                for fname in sorted(os.listdir(jenis_path)):
                    if fname.lower().endswith(".nc"):
                        add_file(variabel, skenario, periode, jenis,
                                  fname, os.path.join(jenis_path, fname))

    for variabel in sorted(os.listdir(root)):
        var_path = os.path.join(root, variabel)
        if not os.path.isdir(var_path):
            continue

        for top in sorted(os.listdir(var_path)):
            top_path = os.path.join(var_path, top)
            if not os.path.isdir(top_path):
                continue

            if re.match(r"historical|baseline|observasi", top, re.I):
                # VARIABEL/historical/PERIODE/JENIS/MODEL.nc
                walk_periode_jenis_model(variabel, top, top_path)

            elif re.match(r"future|proyeksi|projection", top, re.I):
                # VARIABEL/future/SKENARIO/PERIODE/JENIS/MODEL.nc
                for skenario in sorted(os.listdir(top_path)):
                    sk_path = os.path.join(top_path, skenario)
                    if os.path.isdir(sk_path):
                        walk_periode_jenis_model(variabel, skenario, sk_path)

            else:
                # Fallback: anggap 'top' langsung sebagai nama skenario,
                # mendukung struktur lama VARIABEL/SKENARIO/PERIODE/JENIS/MODEL.nc
                walk_periode_jenis_model(variabel, top, top_path)

    return index


@lru_cache(maxsize=256)
def read_nc(path):
    """Baca file NetCDF, ambil lat/lon dan variabel data pertama (cached)."""
    ds = xr.open_dataset(path)
    data_vars = list(ds.data_vars)
    if not data_vars:
        raise ValueError(f"Tidak ada data variable di {path}")
    varname = data_vars[0]

    lat = ds["lat"].values if "lat" in ds.coords else ds["latitude"].values
    lon = ds["lon"].values if "lon" in ds.coords else ds["longitude"].values
    z   = ds[varname].values

    # Pastikan urutan dimensi (lat, lon)
    if z.shape != (len(lat), len(lon)):
        z = z.T

    z = np.where(np.isnan(z), None, np.round(z.astype(float), 4))

    return {
        "varname": varname,
        "lat": np.round(lat, 3).tolist(),
        "lon": np.round(lon, 3).tolist(),
        "z": z.tolist(),
    }


@app.route("/")
def index_page():
    return render_template("index.html")


@app.route("/api/ui_config")
def api_ui_config():
    """Kembalikan konfigurasi mapping label untuk model dan skenario."""
    path = os.environ.get("UI_CONFIG", "config_ui.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return jsonify(json.load(f))
        except Exception as e:
            log.error("Gagal membaca UI config %s: %s", path, e)
    return jsonify({})


@app.route("/api/options")
def api_options():
    """Kembalikan seluruh pohon metadata (untuk mengisi dropdown bertingkat)."""
    return jsonify(INDEX)


@app.route("/api/color_scales")
def api_color_scales():
    """Kembalikan color scales JSON untuk membaca nama variabel dan tipe index."""
    return jsonify(COLOR_CONFIG)


@app.route("/api/data")
def api_data():
    kategori = request.args.get("kategori")
    variabel = request.args.get("variabel")
    skenario = request.args.get("skenario")
    periode = request.args.get("periode")
    jenis = request.args.get("jenis")
    model = request.args.get("model")

    try:
        path = INDEX[kategori][variabel][skenario][periode][jenis][model]
    except KeyError:
        return jsonify({"error": "Kombinasi pilihan tidak ditemukan di data."}), 404

    try:
        payload = read_nc(path)
    except Exception as e:
        log.exception("Gagal membaca %s", path)
        return jsonify({"error": f"Gagal membaca file: {e}"}), 500

    payload.update({
        "kategori": kategori, "variabel": variabel, "skenario": skenario,
        "periode": periode, "jenis": jenis, "model": model,
    })

    scale = get_color_scale(variabel, jenis)
    if scale:
        payload["color_scale"] = scale

    var_config = COLOR_CONFIG.get(variabel) or COLOR_CONFIG.get(variabel.upper()) or {}
    payload["var_label"] = var_config.get("name", variabel)

    return jsonify(payload)


ensure_plotly_js()
COLOR_CONFIG = load_color_config(COLOR_CONFIG_PATH)
roots = parse_data_roots()
INDEX = {}
total_files = 0
for label, path in roots.items():
    sub_index = build_index(path)
    n = sum(
        1
        for v in sub_index.values()
        for s in v.values()
        for p in s.values()
        for j in p.values()
        for _ in j.values()
    )
    log.info("Kategori '%s' (%s): %d file .nc ditemukan", label, path, n)
    if n > 0:
        INDEX[label] = sub_index
    total_files += n
log.info("Total %d file .nc di seluruh kategori", total_files)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)