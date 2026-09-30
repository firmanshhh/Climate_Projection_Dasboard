import os
import math
import numpy as np
import geopandas as gpd
import xarray as xr
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import cartopy.crs as ccrs
from cartopy.feature import ShapelyFeature
from cartopy.io.shapereader import Reader
import matplotlib

def apply_default_plot_settings():
    """Menerapkan konfigurasi plot matplotlib default untuk project ini."""
    plt.rcParams.update({
        'figure.figsize': (7.2, 4.5),
        'figure.dpi': 300,
        'font.family': 'sans-serif',
        'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans', 'Liberation Sans'],
        'font.size': 10,
        'axes.labelsize': 11,
        'axes.titlesize': 12,
        'xtick.labelsize': 10,
        'ytick.labelsize': 10,
        'legend.fontsize': 10,
        'legend.frameon': False,
        'legend.loc': 'upper left',
        'axes.linewidth': 0.8,
        'xtick.major.width': 0.8,
        'ytick.major.width': 0.8,
        'xtick.minor.visible': True,
        'ytick.minor.visible': True,
        'xtick.minor.width': 0.6,
        'ytick.minor.width': 0.6,
        'grid.linestyle': ':',
        'grid.alpha': 0.4,
        'axes.spines.top': False,
        'axes.spines.right': False,
        'lines.linewidth': 1.5,
        'lines.markersize': 5,
    })

def deg_to_degmin_lat(x):
    """Konversi derajat desimal ke string derajat-menit (° ' ) untuk lintang."""
    is_neg = x < 0
    x = abs(x)
    deg = int(x)
    minute = round((x - deg) * 60)
    
    if deg == 0:
        return f"{deg}°{minute:02d}'"
    else:
        sign = '0"S' if is_neg else '0"N'
        return f"{deg}°{minute:01d}'{sign}"

def deg_to_degmin_lon(x):
    """Konversi derajat desimal ke string derajat-menit (° ' ) untuk bujur."""
    is_neg = x < 0
    x = abs(x)
    deg = int(x)
    minute = round((x - deg) * 60)
    sign = '0"W' if is_neg else '0"E'
    return f"{deg}°{minute:01d}'{sign}"

def custom_cmap(color1="#ffffff", color2="#1eafe8", n_colors=200):
    """Membuat custom colormap dari 2 warna (opsional logik gradient)."""
    start_rgb = np.array(mcolors.hex2color(color1))
    end_rgb   = np.array(mcolors.hex2color(color2))
    colors = []
    for i in range(n_colors):
        ratio = i / (n_colors - 1)
        rgb = start_rgb * (1 - ratio) + end_rgb * ratio
        hex_color = f"#{int(rgb[0]*255):02x}{int(rgb[1]*255):02x}{int(rgb[2]*255):02x}"
        colors.append(hex_color)
    return mcolors.ListedColormap(colors)


class SpatialDataLoader:
    """Class untuk membantu meloading shapefile/geospasial dengan rapih."""
    def __init__(self, base_path='/mnt/dataset/02_REPO_GITHUB_FIRMAN/Developing_Advance_Climate_Visualization/data/spasial'):
        self.base_path = base_path
        
    def get_cartopy_feature(self, relative_path):
        """Memuat shapefile sebagai object ShapelyFeature Cartopy (cocok dgn ax.add_feature)."""
        full_path = os.path.join(self.base_path, relative_path)
        return ShapelyFeature(Reader(full_path).geometries(), ccrs.PlateCarree())

    def get_geodataframe(self, relative_path):
        """Memuat shapefile sebagai objek GeoPandas DataFrame (untuk di-plot manual)."""
        full_path = os.path.join(self.base_path, relative_path)
        gdf = gpd.read_file(full_path)
        if gdf.crs != "EPSG:4326":
            gdf.to_crs("EPSG:4326", inplace=True)
        return gdf

    def get_bedrock_data(self, relative_path='Batimetry/BedrockCLIP.nc'):
        """Memuat data Bedrock Topografi (xarray Dataset)."""
        full_path = os.path.join(self.base_path, relative_path)
        return xr.open_dataset(full_path)

def plot_shape_boundary(geodataframe, ax, color='#599ae2', linewidth=0.5, linestyle='--', zorder=2, alpha=1):
    """Plot GeoPandas (Polygon / MultiPolygon) secara iteratif ke axes cartopy map."""
    for _, row in geodataframe.iterrows():
        geom = row.geometry
        if geom.geom_type == 'LineString':
            x, y = geom.xy
            ax.plot(x, y, color=color, linewidth=linewidth, linestyle=linestyle,
                    transform=ccrs.PlateCarree(), zorder=zorder, alpha=alpha)
        elif geom.geom_type == 'MultiPolygon':
            for poly in geom.geoms:
                x, y = poly.exterior.xy
                ax.plot(x, y, color=color, linewidth=linewidth, linestyle=linestyle,
                        transform=ccrs.PlateCarree(), zorder=zorder, alpha=alpha)
        elif geom.geom_type == 'Polygon':
            x, y = geom.exterior.xy
            ax.plot(x, y, color=color, linewidth=linewidth, linestyle=linestyle,
                    transform=ccrs.PlateCarree(), zorder=zorder, alpha=alpha)


def add_scale_bar_boxes(ax, length_km, location=(0.05, 0.05), n_segments=8, color='black', fontsize=8, linewidth=1):
    """Scale bar gaya kotak hitam-putih bergantian."""
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    center_lat = (y0 + y1) / 2
    km_per_deg_lon = 111.32 * math.cos(math.radians(center_lat))
    length_deg = length_km / km_per_deg_lon

    pos_x = x0 + location[0] * (x1 - x0)
    pos_y = y0 + location[1] * (y1 - y0)
    segment_length = length_deg / n_segments
    segment_height = 0.25

    for i in range(n_segments):
        x_start = pos_x + i * segment_length
        facecolor = 'black' if i % 2 == 0 else 'white'
        rect = mpatches.Rectangle(
            (x_start, pos_y),
            segment_length, segment_height,
            linewidth=linewidth, edgecolor=color, facecolor=facecolor,
            transform=ax.projection, zorder=10
        )
        ax.add_patch(rect)

    ax.text(pos_x, pos_y - 0.3, '0', ha='center', va='top', fontsize=fontsize, color=color, transform=ax.projection, zorder=10)
    ax.text(pos_x + length_deg, pos_y - 0.3, str(length_km), ha='center', va='top', fontsize=fontsize, color=color, transform=ax.projection, zorder=10)
    ax.text(pos_x + length_deg + 0.05, pos_y - 0.3, '   km', ha='left', va='top', fontsize=fontsize, color=color, transform=ax.projection, zorder=10)


def add_logos_and_text(fig, ax, logo_path='/mnt/dataset/02_REPO_GITHUB_FIRMAN/Developing_Advance_Climate_Visualization/data/img/logo.png', arahangin_path='data/img/ArahAngin.png', data_source_text="Sumber Data: (Data Observasi BMKG)"):
    """Menambahkan aksesoris map (Logo BMKG, Arah Angin, Footer)."""
    # 1. Logo Utama (Pojok atas)
    try:
        if os.path.exists(logo_path):
            logo     = plt.imread(logo_path)
            imagebox = OffsetImage(logo, zoom=0.045)
            ab       = AnnotationBbox(imagebox, (0.91, 0.78), xycoords='axes fraction', frameon=False, pad=0.0, box_alignment=(0, 0), zorder=10)
            ax.add_artist(ab)
    except Exception as e:
        print(f"Warning: Logo BMKG tidak bisa dimuat ({e})")
        
    # 2. Arah Angin (Pojok Bawah)
    try:
        if os.path.exists(arahangin_path):
            angin    = plt.imread(arahangin_path)
            anginbox = OffsetImage(angin, zoom=0.1)
            ag       = AnnotationBbox(anginbox, (0.03, 0.08), xycoords='axes fraction', frameon=False, pad=0.0, box_alignment=(0, 0), zorder=11)
            ax.add_artist(ag)
    except Exception as e:
        print(f"Warning: Arah Angin tidak bisa dimuat ({e})")

    if data_source_text:
        plt.figtext(0.785, 0.2825, data_source_text, ha='center', va='bottom', fontsize=10, fontweight='medium')

class AdaptiveLegendManager:
    """Manajer legend dinamis dengan tingkat ukuran dot yang sepenuhnya dinamis.

    Parameters
    ----------
    size_levels : int atau tuple(int, int)
        • int         → jumlah level ukuran **sama** untuk sisi negatif & positif
        • (n_neg, n_pos) → level **berbeda** per sisi, mis. (3, 5)

    Cara kerja
    ----------
    • Faktor ukuran dihitung otomatis dengan ``np.linspace(_MIN_FACTOR, _MAX_FACTOR, n)``
      sehingga tidak ada nama kategori hardcode (kecil/sedang/besar).
    • Threshold per sisi dihitung proporsional terhadap max-abs masing-masing sisi,
      sehingga interval asimetris tetap memakai semua level secara penuh.
    • Level = 1 → semua dot seragam (uniform).

    Contoh
    ------
    >>> mgr = AdaptiveLegendManager(edges=[-0.75,-0.5,-0.25,0,0.25,0.5,0.75,1.0,1.5],
    ...                             base_size=50, size_levels=(3, 5))
    """

    _MIN_FACTOR = 0.20   # faktor relatif dot terkecil
    _MAX_FACTOR = 1.20   # faktor relatif dot terbesar

    # ------------------------------------------------------------------ init
    def __init__(self, min_val=None, max_val=None, n_segments=None,
                 edges=None, cmap='RdBu_r', base_size=30, size_levels=3):

        # --- validasi mode input ------------------------------------------
        mode1 = all(x is not None for x in [min_val, max_val, n_segments])
        mode2 = edges is not None
        if mode1 and mode2:
            raise ValueError("Gunakan HANYA SALAH SATU: (min_val, max_val, n_segments) ATAU (edges)")
        if not mode1 and not mode2:
            raise ValueError("Harus menyediakan (min_val, max_val, n_segments) ATAU (edges)")

        if mode1:
            if min_val >= max_val: raise ValueError("min_val harus < max_val")
            if n_segments < 1:    raise ValueError("n_segments minimal 1")
            self.edges = np.linspace(min_val, max_val, n_segments + 1)
            self.min_val, self.max_val, self.n_segments = float(min_val), float(max_val), int(n_segments)
        else:
            if len(edges) < 2: raise ValueError("edges minimal 2 nilai")
            self.edges = np.array(sorted(edges), dtype=float)
            self.min_val, self.max_val, self.n_segments = self.edges[0], self.edges[-1], len(self.edges) - 1

        # --- max-abs terpisah per sisi ------------------------------------
        neg_vals = [e for e in self.edges if e < 0]
        pos_vals = [e for e in self.edges if e > 0]
        self.max_abs_neg = abs(min(neg_vals)) if neg_vals else 0.0
        self.max_abs_pos = max(pos_vals)       if pos_vals else 0.0
        # fallback jika salah satu sisi kosong
        if self.max_abs_neg == 0.0: self.max_abs_neg = self.max_abs_pos
        if self.max_abs_pos == 0.0: self.max_abs_pos = self.max_abs_neg
        self.max_abs = max(self.max_abs_neg, self.max_abs_pos)  # backward-compat

        # --- parse size_levels -------------------------------------------
        if isinstance(size_levels, (tuple, list)):
            n_neg, n_pos = int(size_levels[0]), int(size_levels[1])
        else:
            n_neg = n_pos = int(size_levels)
        if n_neg < 1 or n_pos < 1:
            raise ValueError("Setiap sisi size_levels minimal 1")

        self.n_size_neg  = n_neg
        self.n_size_pos  = n_pos
        self.size_levels = (n_neg, n_pos)   # simpan selalu sebagai tuple
        self.base_size   = base_size

        # --- faktor ukuran via linspace  --------------------------------
        # MAX_FACTOR tiap sisi discale proporsional terhadap max_abs global
        # → sisi dengan nilai lebih kecil mendapat dot terbesar yang lebih kecil pula
        # → mencerminkan perbedaan absolut yang benar antar kedua sisi
        _range = self._MAX_FACTOR - self._MIN_FACTOR
        _max_f_neg = self._MIN_FACTOR + _range * (self.max_abs_neg / self.max_abs)
        _max_f_pos = self._MIN_FACTOR + _range * (self.max_abs_pos / self.max_abs)

        self._factors_neg = (np.array([1.0])
                             if n_neg == 1 else
                             np.linspace(self._MIN_FACTOR, _max_f_neg, n_neg))
        self._factors_pos = (np.array([1.0])
                             if n_pos == 1 else
                             np.linspace(self._MIN_FACTOR, _max_f_pos, n_pos))

        # --- threshold pembatas antar level -------------------------------------
        # BUG FIX 1: Hitung jumlah SEGMEN (bukan jumlah edge) menggunakan midpoint.
        #   → untuk data all-positif, len(pos_vals)=9 edge padahal segmennya 8.
        n_pos_segs = sum(1 for i in range(len(self.edges)-1)
                         if (self.edges[i] + self.edges[i+1]) / 2 > 0)
        n_neg_segs = sum(1 for i in range(len(self.edges)-1)
                         if (self.edges[i] + self.edges[i+1]) / 2 < 0)

        # BUG FIX 2: Pilihan threshold berdasarkan tipe data:
        #   • Data MIXED (ada negatif & positif):
        #       pos edge-aligned → pos_vals[:-1]  (batas kiri implisit dari sisi neg)
        #       neg edge-aligned → neg_abs[:-1]
        #   • Data ALL-POSITIVE atau ALL-NEGATIVE:
        #       edge-aligned → inner edges (buang leftmost DAN rightmost)
        #       fallback     → linspace dalam rentang edge aktual [min_edge, max_edge]
        _all_positive = (not neg_vals)
        _all_negative = (not pos_vals)

        _sorted_pos = sorted(pos_vals)
        if n_pos > 1:
            if n_pos == n_pos_segs:               # edge-aligned
                if _all_positive:
                    self.thresholds_pos = _sorted_pos[1:-1]   # inner edges saja
                else:
                    self.thresholds_pos = _sorted_pos[:-1]    # kiri implisit dari neg
            else:                                 # fallback
                _p0 = _sorted_pos[0] if _all_positive else 0.0
                _p1 = self.max_abs_pos
                self.thresholds_pos = [_p0 + (_p1 - _p0) * i / n_pos
                                       for i in range(1, n_pos)]
        else:
            self.thresholds_pos = []

        _sorted_neg_abs = sorted(abs(e) for e in neg_vals)
        if n_neg > 1:
            if n_neg == n_neg_segs:               # edge-aligned
                if _all_negative:
                    self.thresholds_neg = _sorted_neg_abs[1:-1]  # inner edges saja
                else:
                    self.thresholds_neg = _sorted_neg_abs[:-1]   # kiri implisit dari pos
            else:                                 # fallback
                _n0 = _sorted_neg_abs[0] if _all_negative else 0.0
                _n1 = self.max_abs_neg
                self.thresholds_neg = [_n0 + (_n1 - _n0) * i / n_neg
                                       for i in range(1, n_neg)]
        else:
            self.thresholds_neg = []

        self.thresholds = self.thresholds_pos   # backward-compat

        # --- colormap ----------------------------------------------------
        if isinstance(cmap, str):
            self.colors = matplotlib.colormaps.get_cmap(cmap)(np.linspace(0, 1, self.n_segments))
        else:
            self.colors = cmap(np.linspace(0, 1, self.n_segments))

    # --------------------------------------------------------- internal helper
    def _get_size_factor(self, value):
        """Kembalikan faktor ukuran (float) untuk satu nilai skalar.

        Pilih array faktor & threshold berdasarkan tanda nilai, lalu hitung
        berapa threshold yang terlampaui → itulah indeks level ukurnya.
        """
        value = float(value)
        if value < 0:
            factors, thresholds = self._factors_neg, self.thresholds_neg
        else:
            factors, thresholds = self._factors_pos, self.thresholds_pos

        abs_val = abs(value)
        idx = sum(1 for t in thresholds if abs_val > t)    # jumlah batas terlampaui
        return float(factors[min(idx, len(factors) - 1)])

    # --------------------------------------------------------- public API
    def get_sizes(self, values):
        """Kembalikan array ukuran dot (``s``) untuk seluruh nilai input."""
        return np.array([self.base_size * self._get_size_factor(v)
                         for v in np.asarray(values, dtype=float)])

    def get_legend_radius(self, value=None, size_factor=None):
        """Kembalikan jari-jari circle untuk legend.

        Parameters
        ----------
        value       : nilai data – prioritas utama, faktor dihitung otomatis
        size_factor : override manual faktor ukuran (float)
        """
        if value is not None:
            factor = self._get_size_factor(value)
        elif size_factor is not None:
            factor = float(size_factor)
        else:
            factor = 1.0
        return 0.02 * np.sqrt((self.base_size * factor) / 30.0)

    def get_segment_index(self, value):
        value = float(value)
        if value < self.edges[0]:   return 0
        if value >= self.edges[-1]: return self.n_segments - 1
        return int(min(np.searchsorted(self.edges, value, side='right') - 1,
                       self.n_segments - 1))

    def plot_scatter(self, lons, lats, values, ax=None,
                     edgecolor='black', linewidth=0.25, alpha=0.95):
        lons   = np.asarray(lons,   dtype=float)
        lats   = np.asarray(lats,   dtype=float)
        values = np.asarray(values, dtype=float)
        if not (len(lons) == len(lats) == len(values)):
            raise ValueError("Panjang lons, lats, dan values harus sama")

        colors = [self.colors[self.get_segment_index(val)] for val in values]
        if ax is None:
            _, ax = plt.subplots(figsize=(10, 6))
        return ax.scatter(lons, lats, c=colors, s=self.get_sizes(values),
                          edgecolor=edgecolor, linewidth=linewidth,
                          alpha=alpha, zorder=11)

    def add_legend(self, ax, n_columns=1, font_size=9, circle_linewidth=0.6,
                   spacing=None, y_start=0.725, decimal=None):
        """Tambahkan legend warna + ukuran ke axes.

        Parameters
        ----------
        decimal : int atau None
            Jumlah angka di belakang koma pada label colorbar.
            ``None``  → otomatis (≥10 dibulatkan, sisanya 2 desimal)
            ``0``     → bulat (26)
            ``1``     → 1 desimal (26.5)
            ``2``     → 2 desimal (26.50)  ← sama dgn default lama
        """
        if spacing is None:
            spacing = {'dy': 0.125, 'dx_col': 0.55}

        def format_value(val):
            val = float(val)
            if decimal is not None:
                # Mode eksplisit: gunakan presisi yang diminta
                if val < 0:
                    return f"(-{abs(val):.{decimal}f})" if val != 0 else "0"
                return f"{val:.{decimal}f}"
            # Mode otomatis (perilaku lama)
            if val == 0:          return "0.0"
            if abs(val) >= 10:    return f"-({int(abs(val))})" if val < 0 else f"{int(val)}"
            return f"(-{abs(val):.2f})" if val < 0 else f"{val:.2f}"

        items_per_col = int(np.ceil(self.n_segments / n_columns))
        for i in range(self.n_segments):
            col, row = i // items_per_col, i % items_per_col
            x_pos    = 0.225 + col * spacing['dx_col']
            y_pos    = y_start - row * spacing['dy']

            midpoint = (self.edges[i] + self.edges[i + 1]) / 2
            radius   = self.get_legend_radius(value=midpoint)
            ax.add_patch(mpatches.Circle(xy=(x_pos, y_pos), radius=radius,
                                         facecolor=self.colors[i],
                                         edgecolor='black',
                                         linewidth=circle_linewidth))

            lower, upper = self.edges[i], self.edges[i + 1]
            if i == 0:
                label = f"< {format_value(upper)}"
            elif i == self.n_segments - 1:
                label = f">= {format_value(lower)}"
            else:
                label = f"{format_value(lower)} – {format_value(upper)}"

            ax.text(x_pos + radius + 0.05, y_pos, label,
                    transform=ax.transAxes, ha='left', va='center',
                    fontsize=font_size)

        ax.set_facecolor('none')
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)

