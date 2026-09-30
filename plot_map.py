import io
import os
import re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import xarray as xr
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, BoundaryNorm
import matplotlib.image as mpimg
from src.maps import (
    apply_default_plot_settings, deg_to_degmin_lat, deg_to_degmin_lon,
    custom_cmap, SpatialDataLoader, plot_shape_boundary, add_scale_bar_boxes,
    add_logos_and_text, AdaptiveLegendManager
)
import matplotlib.ticker as mticker


def generate_geotiff(nc_path, var_name, time_idx=0, mask_indo=False):
    try:
        import rioxarray
    except ImportError:
        raise ImportError("rioxarray is required to export GeoTIFF. Please install it in your conda env: conda install -c conda-forge rioxarray")
        
    ds = xr.open_dataset(nc_path)
    if var_name not in ds:
        # Fallback to the first variable if the requested one is not found
        var_name = list(ds.data_vars)[0]
    
    da = ds[var_name]
    
    if 'time' in da.dims:
        da = da.isel(time=time_idx)
        
    # Ensure spatial dims are named 'y' and 'x' for rioxarray
    rename_dict = {}
    if 'latitude' in da.dims: rename_dict['latitude'] = 'y'
    elif 'lat' in da.dims: rename_dict['lat'] = 'y'
    if 'longitude' in da.dims: rename_dict['longitude'] = 'x'
    elif 'lon' in da.dims: rename_dict['lon'] = 'x'
    
    if rename_dict:
        da = da.rename(rename_dict)
        
    da.rio.write_crs("epsg:4326", inplace=True)
    
    if mask_indo:
        gdf = load_indonesia_geojson()
        try:
            da = da.rio.clip(gdf.geometry, gdf.crs, drop=False)
        except Exception:
            pass
            
    buf = io.BytesIO()
    da.rio.to_raster(buf, driver="GTiff")
    buf.seek(0)
    return buf

def generate_csv(nc_path, var_name, time_idx=0, mask_indo=False):
    ds = xr.open_dataset(nc_path)
    if var_name not in ds:
        var_name = list(ds.data_vars)[0]
    
    da = ds[var_name]
    if 'time' in da.dims:
        da = da.isel(time=time_idx)
        
    if mask_indo:
        try:
            import rioxarray
            gdf = load_indonesia_geojson()
            rename_dict = {}
            if 'latitude' in da.dims: rename_dict['latitude'] = 'y'
            elif 'lat' in da.dims: rename_dict['lat'] = 'y'
            if 'longitude' in da.dims: rename_dict['longitude'] = 'x'
            elif 'lon' in da.dims: rename_dict['lon'] = 'x'
            
            da_temp = da.rename(rename_dict) if rename_dict else da
            da_temp = da_temp.rio.write_crs("epsg:4326")
            # For CSV, drop=True is preferred so we don't include millions of NaNs
            da_clipped = da_temp.rio.clip(gdf.geometry, gdf.crs, drop=True)
            
            reverse_rename = {v: k for k, v in rename_dict.items()}
            da = da_clipped.rename(reverse_rename) if reverse_rename else da_clipped
        except Exception:
            pass

    df = da.to_dataframe().reset_index()
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    # Return as BytesIO because zipfile writestr expects bytes or string, 
    # but to be safe and consistent we encode to bytes
    bytes_buf = io.BytesIO(buf.getvalue().encode('utf-8'))
    return bytes_buf

from functools import lru_cache

@lru_cache(maxsize=1)
def load_indonesia_geojson():
    try:
        import geopandas as gpd
    except ImportError:
        raise ImportError("geopandas is required for Indonesia average. Please install it (e.g. conda install -c conda-forge geopandas).")
    # Base dir assumes this is run from app root
    geojson_path = os.path.join("static", "geojson", "indonesia-38-provinces.geojson")
    if not os.path.exists(geojson_path):
        raise FileNotFoundError(f"GeoJSON file not found at {geojson_path}")
    return gpd.read_file(geojson_path)

def get_spatial_average(nc_path, var_name, time_idx=0, mask_indo=True):
    try:
        import rioxarray
    except ImportError:
        raise ImportError("rioxarray is required for spatial average calculation. Please install it.")
        
    ds = xr.open_dataset(nc_path)
    if var_name not in ds:
        var_name = list(ds.data_vars)[0]
    
    da = ds[var_name]
    if 'time' in da.dims:
        da = da.isel(time=time_idx)
        
    rename_dict = {}
    if 'latitude' in da.dims: rename_dict['latitude'] = 'y'
    elif 'lat' in da.dims: rename_dict['lat'] = 'y'
    if 'longitude' in da.dims: rename_dict['longitude'] = 'x'
    elif 'lon' in da.dims: rename_dict['lon'] = 'x'
    
    if rename_dict:
        da = da.rename(rename_dict)
        
    da = da.rio.write_crs("epsg:4326")
    
    if mask_indo:
        gdf = load_indonesia_geojson()
        try:
            da = da.rio.clip(gdf.geometry, gdf.crs, drop=True)
        except Exception:
            pass # Fallback to unclipped if clip fails
            
    # Weight by cos(lat) for accurate spatial mean
    weights = np.cos(np.deg2rad(da.y))
    weights.name = "weights"
    da_weighted = da.weighted(weights)
    mean_val = float(da_weighted.mean().values)
    return mean_val

def build_annotation(subtitle, ds=None, quantity="Klimatologi", sep="\n"):
    """
    Bangun teks annotation, satu item per baris (sep="\\n"):
        Dataset: CORDEX (MIROC-ES2L-LS)
        Period: 1981-2010
        Quantity: Klimatologi
        Scenario: Historical
    Gunakan sep=" - " untuk satu baris.
    Prioritas sumber: subtitle -> atribut NetCDF -> default.
    """
    text = subtitle or ""
    attrs = ds.attrs if ds is not None else {}

    # Dataset
    dataset = (attrs.get("project_id") or attrs.get("project")
               or attrs.get("activity_id") or "CORDEX")
    m = re.search(r'\b(CORDEX|CMIP[56]?|ERA5|CHIRPS)\b', text, re.I)
    if m:
        dataset = m.group(1).upper()

    # Model
    model = (attrs.get("source_id") or attrs.get("driving_model_id")
             or attrs.get("model_id") or "")
    m = re.search(r'\(([^)]+)\)', text)
    if m:
        model = m.group(1)
    dataset_str = f"{dataset} ({model})" if model else dataset

    # Period
    period = ""
    m = re.search(r'(\d{4})\s*[-–]\s*(\d{4})', text)
    if m:
        period = f"{m.group(1)}-{m.group(2)}"
    elif ds is not None and "time" in ds.coords and ds.time.size > 0:
        try:
            period = f"{int(ds.time.dt.year.min())}-{int(ds.time.dt.year.max())}"
        except Exception:
            pass

    # Scenario
    scenario = attrs.get("experiment_id") or attrs.get("experiment") or ""
    m = re.search(r'\b(historical|ssp\d{3}|rcp\d{2}|rcp\d\.\d)\b', text, re.I)
    if m:
        scenario = m.group(1)
    if re.match(r'(?i)(ssp|rcp)', scenario):
        scenario = scenario.upper()
    else:
        scenario = scenario.capitalize()

    parts = [f"Dataset: {dataset_str}"]
    if period:
        parts.append(f"Period: {period}")
    if quantity:
        parts.append(f"Quantity: {quantity}")
    if scenario:
        parts.append(f"Scenario: {scenario}")
    return sep.join(parts)


def generate_map_plot(nc_path, var_name, time_idx, vmin, vmax, palette_hex_list,
                      is_discrete, num_bins, title, subtitle, unit,
                      quantity="Klimatologi",
                      annotation_offset=0.085,
                      annotation_fontsize=8,
                      mask_indo=False):
    ds = xr.open_dataset(nc_path)
    try:
        if var_name not in ds.data_vars:
            for v in ds.data_vars:
                if len(ds[v].dims) >= 2:
                    var_name = v
                    break

        # Dibangun sebelum slicing waktu agar Period bisa diambil dari coords
        annotation = build_annotation(subtitle, ds=ds, quantity=quantity)

        da = ds[var_name]
        if 'time' in da.dims:
            if time_idx < len(da.time):
                da = da.isel(time=time_idx)
            else:
                da = da.isel(time=0)

        if mask_indo:
            try:
                import rioxarray
                gdf = load_indonesia_geojson()
                rename_dict = {}
                if 'latitude' in da.dims: rename_dict['latitude'] = 'y'
                elif 'lat' in da.dims: rename_dict['lat'] = 'y'
                if 'longitude' in da.dims: rename_dict['longitude'] = 'x'
                elif 'lon' in da.dims: rename_dict['lon'] = 'x'
                
                da_temp = da.rename(rename_dict) if rename_dict else da
                da_temp = da_temp.rio.write_crs("epsg:4326")
                da_clipped = da_temp.rio.clip(gdf.geometry, gdf.crs, drop=False)
                
                reverse_rename = {v: k for k, v in rename_dict.items()}
                da = da_clipped.rename(reverse_rename) if reverse_rename else da_clipped
            except Exception:
                pass

        lon_dim = 'lon' if 'lon' in da.dims else 'longitude'
        lat_dim = 'lat' if 'lat' in da.dims else 'latitude'

        lons = da[lon_dim].values
        lats = da[lat_dim].values
        values = da.values

        if is_discrete:
            cmap = LinearSegmentedColormap.from_list("custom", palette_hex_list, N=num_bins)
            bounds = np.linspace(vmin, vmax, num_bins + 1)
            norm = BoundaryNorm(bounds, cmap.N)
        else:
            cmap = LinearSegmentedColormap.from_list("custom", palette_hex_list)
            norm = matplotlib.colors.Normalize(vmin=vmin, vmax=vmax)

        fig = plt.figure(figsize=(12, 10))
        ax = plt.axes(projection=ccrs.PlateCarree())

        ax.set_extent([92, 142, -12, 8])
        for spine in ax.spines.values():
            spine.set_linewidth(1.8)
        fig.patch.set_edgecolor('none')
        fig.patch.set_linewidth(3)

        # Gridlines
        gl = ax.gridlines(draw_labels=True, linewidth=0.01, color='gray',
                          alpha=0.7, linestyle='--')
        gl.xlocator = mticker.FixedLocator(range(90, 150, 20))
        gl.ylocator = mticker.FixedLocator(range(-15, 12, 10))
        gl.xformatter = mticker.FuncFormatter(lambda x, pos: deg_to_degmin_lon(x))
        gl.yformatter = mticker.FuncFormatter(lambda x, pos: deg_to_degmin_lat(x))
        gl.xlabel_style = {'rotation': 0, 'color': 'black', 'size': 11}
        gl.ylabel_style = {'rotation': 90, 'color': 'black', 'size': 11}

        # Posisi tick (WAJIB, kalau tidak tick tidak muncul)
        ax.set_xticks(range(90, 150, 10), crs=ccrs.PlateCarree())
        ax.set_yticks(range(-15, 12, 10), crs=ccrs.PlateCarree())
        ax.set_xticks(np.arange(90, 150, 5), minor=True, crs=ccrs.PlateCarree())
        ax.set_yticks(np.arange(-15, 12, 5), minor=True, crs=ccrs.PlateCarree())

        # Tampilan tick
        ax.tick_params(which='major', length=10, width=1.0, direction='inout',
                       top=True, right=True, labelbottom=False, labelleft=False)
        ax.tick_params(which='minor', length=6, width=0.8, direction='inout',
                       top=True, right=True)
                    

        ax.add_feature(cfeature.COASTLINE, linewidth=0.8)
        ax.add_feature(cfeature.BORDERS, linewidth=0.5, linestyle=':')

        mesh = ax.pcolormesh(lons, lats, values, cmap=cmap, norm=norm,
                             transform=ccrs.PlateCarree(), shading='auto')

        ax.set_extent([lons.min(), lons.max(), lats.min(), lats.max()],
                      crs=ccrs.PlateCarree())

        title_parts = title.split(' - ')
        main_title = title_parts[0]
        sub_title = title_parts[1] if len(title_parts) > 1 else ""

        plt.suptitle(main_title, fontsize=16, fontweight='bold', y=0.85)
        plt.title(sub_title, fontsize=14, pad=15)

        cbar_kwargs = {'orientation': 'horizontal', 'pad': 0.05, 'aspect': 30, 'shrink': 0.8}
        if is_discrete:
            cbar_kwargs['extend']  = 'both'
            cbar_kwargs['spacing'] = 'uniform'
        else:
            cbar_kwargs['extend']  = 'both'
            cbar_kwargs['spacing'] = 'uniform'

        cbar = fig.colorbar(mesh, ax=ax, **cbar_kwargs)
        cbar.set_label(f"{unit.replace('Units: ', '')}", fontsize=14, fontweight='bold')

        # ===== ANNOTATION: di bawah colorbar, rata kiri (sejajar tepi kiri colorbar) =====
        fig.canvas.draw()  # pastikan posisi axes sudah final
        pos = cbar.ax.get_position()
        fig.text(
            0.15,                          # tepi kiri colorbar
            pos.y0 + 0.15,
            annotation,
            ha='left', va='top',
            multialignment='left',
            linespacing=1.5,
            fontsize=annotation_fontsize, color='black',
        )
        # ========================================================================

        logo_png = os.path.join("static", "icons", "BMKG_Black.png")
        if os.path.exists(logo_png):
            logo = mpimg.imread(logo_png)
            newax = fig.add_axes([0.8, 0.65, 0.08, 0.08], anchor='NW', zorder=10)
            newax.imshow(logo)
            newax.axis('off')

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)
        return buf
    finally:
        ds.close()