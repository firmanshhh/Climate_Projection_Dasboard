#!/usr/bin/env python
# coding: utf-8

# In[1]:


import xarray as xr
import os
import os.path as pa
import numpy as np


# In[2]:


def calc_trend(da, dim='time'):
    """
    Hitung trend linear (slope per tahun) dari xarray DataArray.
    da  : DataArray dengan dimensi waktu (misal 'time' berisi tahun)
    dim : nama dimensi waktu
    """
    # Jika dim berupa datetime, ubah ke tahun (angka) supaya slope per-tahun
    if np.issubdtype(da[dim].dtype, np.datetime64):
        x = da[dim].dt.year
    else:
        x = da[dim]

    da = da.assign_coords({dim: x})

    # polyfit derajat 1 -> hasilnya slope (degree=1) dan intercept (degree=0)
    coeffs = da.polyfit(dim=dim, deg=1)

    slope     = coeffs.polyfit_coefficients.sel(degree=1) * 10
    intercept = coeffs.polyfit_coefficients.sel(degree=0)

    # nilai trend line (fitted values)
    trend = xr.polyval(da[dim], coeffs.polyfit_coefficients)

    return slope, intercept, trend
# slope, intercept, trend = calc_trend(da_annual, dim='time')

def change_value(ref, fut):
    change = fut - ref
    return change

def change_percent(ref, fut):
    change = ((fut - ref) / ref) * 100
    return change


# **A. Historical Dataset**

# In[3]:


datapath = "/mnt/dataset/01_ANALISA/10.Analisa_Iklim_Kegiatan_NC4/B.Analisa_Indek_Ekstrim_Curah_Hujan_Indonesia/01.indices/Data_Final_Interpolasi_Ensemble"
fnamehist    = "MIROC-ESL-INTPOLASI_NEX-GGDP_PLUS_ENSEMBLE_historical_ALL_MODEL_ALL_INDEK.nc"
outdir   = '../proyeksi_curah_hujan'
periode  = 'historical'
ds       = xr.open_dataset(pa.join(datapath, fnamehist))
ds       = ds.rename({'year':'time'})


# In[4]:


for rentang in ['1981_2010','1991_2020']:
    if rentang =='1981_2010':
        da       = ds.sel(time=slice('1981','2010'))
        da_mean  = da.mean(dim='time')
        for par in list(ds.data_vars.keys()):
            for model in da_mean['model'].values:
                outpath_klim  = pa.join(outdir, par, periode, rentang, 'KLIMATOLOGI')
                outpath_trend = pa.join(outdir, par, periode, rentang, 'TREND')
                os.makedirs(outpath_klim, exist_ok=True)
                os.makedirs(outpath_trend, exist_ok=True)
                # --- A. PROSES & SIMPAN KLIMATOLOGI ---
                da_sel_mean = da_mean[par].sel(model=model)
                if 'model' in da_sel_mean.coords:
                    da_sel_mean = da_sel_mean.drop_vars('model')

                ncname_klim = f'{model}_KLIMATOLOGI_{rentang}.nc'
                da_sel_mean.to_netcdf(pa.join(outpath_klim, ncname_klim))

                # --- B. PROSES & SIMPAN TRENDLINE ---
                # Mengambil nilai kemiringan (slope / degree=1)
                slope, intercept, trend = calc_trend(da[par].sel(model=model), dim='time')
                if 'model' in slope.coords:
                    slope = slope.drop_vars('model')
                if 'degree' in slope.coords:
                    slope = slope.drop_vars('degree')

                # Beri nama variabel yang jelas untuk slope
                slope.name        = f'slope'
                ncname_trend      = f'{model}_TREND_{rentang}.nc'
                slope.to_netcdf(pa.join(outpath_trend, ncname_trend))

    else:
        da      = ds.sel(time=slice('1991','2020'))
        da_mean = da.mean(dim='time') 
        for par in list(ds.data_vars.keys()):
            for model in da_mean['model'].values:
                outpath_klim  = pa.join(outdir, par, periode, rentang, 'KLIMATOLOGI')
                outpath_trend = pa.join(outdir, par, periode, rentang, 'TREND')
                os.makedirs(outpath_klim, exist_ok=True)
                os.makedirs(outpath_trend, exist_ok=True)
                # --- A. PROSES & SIMPAN KLIMATOLOGI ---
                da_sel_mean = da_mean[par].sel(model=model)
                if 'model' in da_sel_mean.coords:
                    da_sel_mean = da_sel_mean.drop_vars('model')

                ncname_klim = f'{model}_KLIMATOLOGI_{rentang}.nc'
                da_sel_mean.to_netcdf(pa.join(outpath_klim, ncname_klim))

                # --- B. PROSES & SIMPAN TRENDLINE ---
                # Mengambil nilai kemiringan (slope / degree=1)
                slope, intercept, trend = calc_trend(da[par].sel(model=model), dim='time')
                if 'model' in slope.coords:
                    slope = slope.drop_vars('model')
                if 'degree' in slope.coords:
                    slope = slope.drop_vars('degree')

                # Beri nama variabel yang jelas untuk slope
                slope.name        = f'slope'
                ncname_trend      = f'{model}_TREND_{rentang}.nc'
                slope.to_netcdf(pa.join(outpath_trend, ncname_trend))


# **B. Future Dataset**

# In[ ]:


datapath      = "/mnt/dataset/01_ANALISA/10.Analisa_Iklim_Kegiatan_NC4/B.Analisa_Indek_Ekstrim_Curah_Hujan_Indonesia/01.indices/Data_Final_Interpolasi_Ensemble"
outdir        = 'proyeksi_curah_hujan'
periode       = 'future'
da_1981_2010  = ds.sel(time=slice('1981','2010'))
da_1981_2010  = da_1981_2010.mean(dim='time')
da_1991_2020  = ds.sel(time=slice('1991','2020'))
da_1991_2020  = da_1991_2020.mean(dim='time')


# In[ ]:


def change_value(ref, fut):
    change = fut - ref
    return change

def change_percent(ref, fut):
    change = ((fut - ref) / ref) * 100
    return change


# In[ ]:


for scenario in ['ssp245','ssp370','ssp585']:
    fname    = f"MIROC-ESL-INTPOLASI_NEX-GGDP_PLUS_ENSEMBLE_{scenario}_ALL_MODEL_ALL_INDEK.nc"
    ds       = xr.open_dataset(pa.join(datapath, fname))
    ds       = ds.rename({'year':'time'})
    for rentang in ['2021_2050','2071_2100']:
        if rentang =='2021_2050':
            da       = ds.sel(time=slice('2021','2050'))
            da_mean  = da.mean(dim='time')
            for par in list(ds.data_vars.keys()):
                for model in da_mean['model'].values:
                    outpath_klim   = pa.join(outdir, par, periode, scenario, rentang, 'KLIMATOLOGI')
                    outpath_trend  = pa.join(outdir, par, periode, scenario, rentang, 'TREND')
                    outpath_change = pa.join(outdir, par, periode, scenario, rentang, 'CHANGE')
                    outpath_value  = pa.join(outdir, par, periode, scenario, rentang, 'VALUE')

                    os.makedirs(outpath_klim, exist_ok=True)
                    os.makedirs(outpath_trend, exist_ok=True)
                    os.makedirs(outpath_change, exist_ok=True)
                    os.makedirs(outpath_value, exist_ok=True)            

                    # --- A. PROSES & SIMPAN KLIMATOLOGI ---
                    da_sel_mean = da_mean[par].sel(model=model)
                    da_ref8110  = da_1981_2010[par].sel(model=model).drop_vars('model')
                    da_ref9120  = da_1991_2020[par].sel(model=model).drop_vars('model')

                    if 'model' in da_sel_mean.coords:
                        da_sel_mean = da_sel_mean.drop_vars('model')
                    ncname_klim = f'{model}_KLIMATOLOGI_{rentang}.nc'
                    da_sel_mean.to_netcdf(pa.join(outpath_klim, ncname_klim))


                    change_2150_8110_value   = change_value(ref=da_ref8110, fut=da_sel_mean)
                    change_2150_8110_percent = change_percent(ref=da_ref8110, fut=da_sel_mean)
                    change_2150_9120_value   = change_value(ref=da_ref9120, fut=da_sel_mean)
                    change_2150_9120_percent = change_percent(ref=da_ref9120, fut=da_sel_mean)

                    ncname_change1 = f'{model}_VALUE_2150_8110.nc'
                    ncname_change2 = f'{model}_PERCENT_2150_8110.nc'
                    ncname_change3 = f'{model}_VALUE_2150_9120.nc'
                    ncname_change4 = f'{model}_PERCENT_2150_9120.nc'

                    change_2150_8110_value.to_netcdf(pa.join(outpath_value, ncname_change1))
                    change_2150_8110_percent.to_netcdf(pa.join(outpath_change, ncname_change2))
                    change_2150_9120_value.to_netcdf(pa.join(outpath_value, ncname_change3))
                    change_2150_9120_percent.to_netcdf(pa.join(outpath_change, ncname_change4))


                    # --- C. PROSES & SIMPAN TRENDLINE ---
                    # Mengambil nilai kemiringan (slope / degree=1)
                    slope, intercept, trend = calc_trend(da[par].sel(model=model), dim='time')
                    if 'model' in slope.coords:
                        slope = slope.drop_vars('model')
                    if 'degree' in slope.coords:
                        slope = slope.drop_vars('degree')

                    # Beri nama variabel yang jelas untuk slope
                    slope.name        = f'slope'
                    ncname_trend      = f'{model}_TREND_{rentang}.nc'
                    slope.to_netcdf(pa.join(outpath_trend, ncname_trend))

        else:
            da       = ds.sel(time=slice('2071','2100'))
            da_mean  = da.mean(dim='time') 
            for par in list(ds.data_vars.keys()):
                for model in da_mean['model'].values:
                    outpath_klim   = pa.join(outdir, par, periode, scenario, rentang, 'KLIMATOLOGI')
                    outpath_trend  = pa.join(outdir, par, periode, scenario, rentang, 'TREND')
                    outpath_change = pa.join(outdir, par, periode, scenario, rentang, 'CHANGE')
                    outpath_value  = pa.join(outdir, par, periode, scenario, rentang, 'VALUE')

                    os.makedirs(outpath_klim, exist_ok=True)
                    os.makedirs(outpath_trend, exist_ok=True)
                    os.makedirs(outpath_change, exist_ok=True)
                    os.makedirs(outpath_value, exist_ok=True)            

                    # --- A. PROSES & SIMPAN KLIMATOLOGI ---
                    da_sel_mean = da_mean[par].sel(model=model)
                    da_ref8110  = da_1981_2010[par].sel(model=model).drop_vars('model')
                    da_ref9120  = da_1991_2020[par].sel(model=model).drop_vars('model')

                    if 'model' in da_sel_mean.coords:
                        da_sel_mean = da_sel_mean.drop_vars('model')
                    ncname_klim = f'{model}_KLIMATOLOGI_{rentang}.nc'
                    da_sel_mean.to_netcdf(pa.join(outpath_klim, ncname_klim))

                    # --- B. PROSES PERHITUNGAN DELTA ---
                    change_7100_8110_value   = change_value(ref=da_ref8110, fut=da_sel_mean)
                    change_7100_8110_percent = change_percent(ref=da_ref8110, fut=da_sel_mean)
                    change_7100_9120_value   = change_value(ref=da_ref9120, fut=da_sel_mean)
                    change_7100_9120_percent = change_percent(ref=da_ref9120, fut=da_sel_mean)

                    ncname_change1 = f'{model}_VALUE_7100_8110.nc'
                    ncname_change2 = f'{model}_PERCENT_7100_8110.nc'
                    ncname_change3 = f'{model}_VALUE_7100_9120.nc'
                    ncname_change4 = f'{model}_PERCENT_7100_9120.nc'

                    change_7100_8110_value.to_netcdf(pa.join(outpath_value, ncname_change1))
                    change_7100_8110_percent.to_netcdf(pa.join(outpath_change, ncname_change2))
                    change_7100_9120_value.to_netcdf(pa.join(outpath_value, ncname_change3))
                    change_7100_9120_percent.to_netcdf(pa.join(outpath_change, ncname_change4))


                    # --- C. PROSES & SIMPAN TRENDLINE ---
                    # Mengambil nilai kemiringan (slope / degree=1)
                    slope, intercept, trend = calc_trend(da[par].sel(model=model), dim='time')
                    if 'model' in slope.coords:
                        slope = slope.drop_vars('model')
                    if 'degree' in slope.coords:
                        slope = slope.drop_vars('degree')

                    # Beri nama variabel yang jelas untuk slope
                    slope.name        = f'slope'
                    ncname_trend      = f'{model}_TREND_{rentang}.nc'
                    slope.to_netcdf(pa.join(outpath_trend, ncname_trend))

