import xarray as xr
import os
import os.path as pa
import numpy as np
import warnings

# Mengabaikan peringatan saat melakukan polyfit
warnings.simplefilter('ignore')

def calc_trend(da, dim='time'):
    """
    Hitung trend linear (slope per tahun) dari xarray DataArray.
    Lalu dikalikan 10 agar menjadi trend per dekade.
    """
    if np.issubdtype(da[dim].dtype, np.datetime64):
        x = da[dim].dt.year
    else:
        x = da[dim]

    da = da.assign_coords({dim: x})
    
    coeffs = da.polyfit(dim=dim, deg=1)
    # Dikalikan 10 untuk trend per dekade
    slope     = coeffs.polyfit_coefficients.sel(degree=1) * 10
    intercept = coeffs.polyfit_coefficients.sel(degree=0)
    trend     = xr.polyval(da[dim], coeffs.polyfit_coefficients)
    
    return slope, intercept, trend

def change_value(ref, fut):
    return fut - ref

def change_percent(ref, fut):
    return ((fut - ref) / ref) * 100

def process_dataset(is_suhu=True):
    if is_suhu:
        datapath = "/mnt/dataset/01_ANALISA/10.Analisa_Iklim_Kegiatan_NC4/A.Analisa_Indek_Ekstrim_Suhu_Indonesia/01.indices/Data_Final_Interpolasi_Ensemble"
        fnamehist = "MIROC-ESL-INTPOLASI_NEX-GGDP_PLUS_ENSEMBLE_historical_ALL_MODEL_ALL_INDEK.nc"
        outdir = '../proyeksi_suhu'
        print("=== Memproses Data SUHU ===")
    else:
        datapath = "/mnt/dataset/01_ANALISA/10.Analisa_Iklim_Kegiatan_NC4/B.Analisa_Indek_Ekstrim_Curah_Hujan_Indonesia/01.indices/Data_Final_Interpolasi_Ensemble"
        fnamehist = "MIROC-ESL-INTPOLASI_NEX-GGDP_PLUS_ENSEMBLE_historical_ALL_MODEL_ALL_INDEK.nc"
        outdir = '../proyeksi_curah_hujan'
        print("=== Memproses Data CURAH HUJAN ===")

    # Memuat data historis
    ds_hist = xr.open_dataset(pa.join(datapath, fnamehist)).rename({'year': 'time'})
    
    hist_rentang = ['1981_2010', '1991_2020']
    da_hist_mean = {}
    
    print("Memproses Historical Dataset...")
    for rentang in hist_rentang:
        print(f"  Rentang Historis: {rentang}")
        y1, y2 = rentang.split('_')
        da = ds_hist.sel(time=slice(y1, y2))
        da_mean = da.mean(dim='time')
        da_hist_mean[rentang] = da_mean
        
        for par in list(ds_hist.data_vars.keys()):
            for model in da_mean['model'].values:
                outpath_klim  = pa.join(outdir, par, 'historical', rentang, 'annual', 'KLIMATOLOGI')
                outpath_trend = pa.join(outdir, par, 'historical', rentang, 'annual', 'TREND')
                os.makedirs(outpath_klim, exist_ok=True)
                os.makedirs(outpath_trend, exist_ok=True)
                
                # KLIMATOLOGI
                da_sel_mean = da_mean[par].sel(model=model)
                if 'model' in da_sel_mean.coords:
                    da_sel_mean = da_sel_mean.drop_vars('model')
                da_sel_mean.to_netcdf(pa.join(outpath_klim, f'{model}_KLIMATOLOGI_{rentang}.nc'))
                
                # TREND
                slope, _, _ = calc_trend(da[par].sel(model=model), dim='time')
                if 'model' in slope.coords: slope = slope.drop_vars('model')
                if 'degree' in slope.coords: slope = slope.drop_vars('degree')
                slope.name = 'slope'
                slope.to_netcdf(pa.join(outpath_trend, f'{model}_TREND_{rentang}.nc'))

    # Memproses Data Future
    fut_rentang = ['2021_2050', '2031_2060', '2041_2070', '2051_2080', '2061_2090', '2071_2100', '2021_2100']
    scenarios = ['ssp245', 'ssp370', 'ssp585']
    
    print("Memproses Future Dataset...")
    for scenario in scenarios:
        print(f"  Skenario Proyeksi: {scenario}")
        fname = f"MIROC-ESL-INTPOLASI_NEX-GGDP_PLUS_ENSEMBLE_{scenario}_ALL_MODEL_ALL_INDEK.nc"
        ds_fut = xr.open_dataset(pa.join(datapath, fname)).rename({'year': 'time'})
        
        for rentang in fut_rentang:
            print(f"    Rentang Future: {rentang}")
            y1, y2 = rentang.split('_')
            da = ds_fut.sel(time=slice(y1, y2))
            da_mean = da.mean(dim='time')
            
            for par in list(ds_fut.data_vars.keys()):
                for model in da_mean['model'].values:
                    outpath_klim   = pa.join(outdir, par, 'future', scenario, rentang, 'annual', 'KLIMATOLOGI')
                    outpath_trend  = pa.join(outdir, par, 'future', scenario, rentang, 'annual', 'TREND')
                    outpath_change = pa.join(outdir, par, 'future', scenario, rentang, 'annual', 'CHANGE')
                    outpath_value  = pa.join(outdir, par, 'future', scenario, rentang, 'annual', 'VALUE')

                    os.makedirs(outpath_klim, exist_ok=True)
                    os.makedirs(outpath_trend, exist_ok=True)
                    os.makedirs(outpath_change, exist_ok=True)
                    os.makedirs(outpath_value, exist_ok=True)            

                    # KLIMATOLOGI
                    da_sel_mean = da_mean[par].sel(model=model)
                    if 'model' in da_sel_mean.coords: 
                        da_sel_mean = da_sel_mean.drop_vars('model')
                    da_sel_mean.to_netcdf(pa.join(outpath_klim, f'{model}_KLIMATOLOGI_{rentang}.nc'))

                    # PERHITUNGAN DELTA (CHANGE & VALUE) terhadap semua referensi historis
                    for ref_rentang in hist_rentang:
                        da_ref = da_hist_mean[ref_rentang][par].sel(model=model)
                        if 'model' in da_ref.coords: 
                            da_ref = da_ref.drop_vars('model')
                        
                        val = change_value(ref=da_ref, fut=da_sel_mean)
                        pct = change_percent(ref=da_ref, fut=da_sel_mean)
                        
                        # Menyimpan file dengan nama full (contoh: MIROC6_VALUE_2031_2060_1981_2010.nc)
                        val.to_netcdf(pa.join(outpath_value, f'{model}_VALUE_{rentang}_{ref_rentang}.nc'))
                        pct.to_netcdf(pa.join(outpath_change, f'{model}_PERCENT_{rentang}_{ref_rentang}.nc'))

                    # TREND
                    slope, _, _ = calc_trend(da[par].sel(model=model), dim='time')
                    if 'model' in slope.coords: slope = slope.drop_vars('model')
                    if 'degree' in slope.coords: slope = slope.drop_vars('degree')
                    slope.name = 'slope'
                    slope.to_netcdf(pa.join(outpath_trend, f'{model}_TREND_{rentang}.nc'))
                    
if __name__ == '__main__':
    # 1. Jalankan untuk agregasi SUHU
    process_dataset(is_suhu=True)
    # 2. Jalankan untuk agregasi CURAH HUJAN
    process_dataset(is_suhu=False)
    print("Selesai me-generate seluruh dataset dinamis.")
