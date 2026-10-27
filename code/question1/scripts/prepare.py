"""Rebuild observation QC views and ERA5 hourly units from copied raw files."""
from __future__ import annotations
import json
import numpy as np
import pandas as pd
import xarray as xr
from pyproj import Transformer
from common import ROOT,CFG,INPUT,TABLES,csv_dump,json_dump,sha256

def hard_invalid(s, name):
    if name.startswith(('WS_','FETCH_')) or name in ['TKE(m2/s2)','USTAR(m/s)']:
        return s<0
    if name.startswith('WD_'): return (s<0)|(s>360)
    if name.startswith('RH_'): return (s<0)|(s>100)
    if name.startswith('VWC_'): return (s<0)|(s>1)
    if name in ['Pressure(hPa)','PA(kPa)']: return s<=0
    if name=='Precip(mm)': return s<0
    if name.startswith(('Ta_','soilT_')) or name=='T_SONIC(deg C)': return s< -273.15
    return pd.Series(False,index=s.index)

def prepare_station():
    dictionary=pd.read_csv(ROOT/'metadata/hourly_data_dictionary.csv').fillna('')
    families=[]; qc_families=[]; audit=[]
    for family in ['MET','RADM','SOIL','FLUX']:
        d=pd.concat([pd.read_csv(p, dtype=str) for p in sorted((ROOT/'data/raw/hourly'/family).glob('*.csv'))],ignore_index=True)
        ti=pd.to_datetime(d.iloc[:,0],format='mixed')
        if ti.duplicated().any(): raise ValueError('Duplicate station timestamps')
        # Conservative support: supplier timestamp assumed hourly start, shift to end.
        idx=pd.DatetimeIndex(ti-pd.Timedelta(hours=8)+pd.Timedelta(hours=1),name='time_utc')
        clean=pd.DataFrame(index=idx); qc=pd.DataFrame(index=idx)
        for row in dictionary[dictionary.family==family].itertuples():
            s=pd.to_numeric(d[row.original_column],errors='coerce')
            sentinel=s.isin([9999.9,-9999,-6999]); invalid=hard_invalid(s,row.original_column)
            s=s.mask(sentinel|invalid|~np.isfinite(s))
            clean[row.column_id]=s.to_numpy()
            if row.qc_column_as_supplied:
                qc[row.column_id]=pd.to_numeric(d[row.qc_column_as_supplied],errors='coerce').to_numpy()
            for y in range(2021,2027):
                mask=ti.dt.year.eq(y).to_numpy(); v=s[mask]
                audit.append(dict(variable=row.column_id,family=family,year=y,n=int(mask.sum()),
                  valid=int(v.notna().sum()),invalid_support=int((invalid.to_numpy()&mask).sum()),
                  min=v.min(),max=v.max(),source_qc=bool(row.qc_column_as_supplied)))
        families.append(clean);qc_families.append(qc)
    station=pd.concat(families,axis=1).sort_index();qc=pd.concat(qc_families,axis=1).sort_index()
    # Remove only fully empty endpoints; leave all internal gaps on an hourly grid.
    valid=station.notna().any(axis=1)
    station=station.loc[valid[valid].index.min():valid[valid].index.max()].asfreq('h')
    qc=qc.reindex(station.index)
    csv_dump(station,INPUT/'station_base.csv.gz',True)
    csv_dump(qc,INPUT/'station_qc.csv.gz',True)
    analysis_dictionary=dictionary.assign(provider_timezone='UTC+8',analysis_timezone='UTC',
       main_timestamp_support='original label assumed hourly start; shifted +1h to completed end',
       main_qc_rule='source QC=0 if supplied; independent checks where source QC absent')
    csv_dump(analysis_dictionary,ROOT/'metadata/analysis_variable_dictionary.csv')
    csv_dump(pd.DataFrame(audit),TABLES/'station_variable_year_quality.csv')
    return station,qc

def station_view(station,qc,policy='qc0',review=True,flux_strict=False,label='start'):
    d=station.copy()
    accepted={'qc0':[0],'qc04':[0,4],'qc0149':[0,1,4,9]}[policy]
    for c in qc: d[c]=d[c].where(qc[c].isin(accepted))
    if review:
        # Longwave components are magnitudes. Preserve small shortwave zero offsets.
        for c in ['radm__rld','radm__rlu']: d[c]=d[c].where(d[c]>0)
        for c in ['radm__rsd','radm__rsu']: d[c]=d[c].where(d[c]>=CFG['shortwave_review_lower'])
    if flux_strict:
        for c,b in [('flux__h',CFG['flux_sensitivity_abs_H']),('flux__le',CFG['flux_sensitivity_abs_LE'])]:
            d[c]=d[c].where(d[c].abs()<=b)
    if label=='end': d.index=d.index-pd.Timedelta(hours=1)
    return d

def deaccumulate(series):
    """At 01 UTC keep daily first step; otherwise require previous contiguous hour."""
    dt=pd.DatetimeIndex(series.index)
    out=series-series.shift(1)
    out[dt.hour==1]=series[dt.hour==1]
    gap=np.r_[True,(dt[1:]-dt[:-1])!=pd.Timedelta(hours=1)]
    out.loc[gap & (dt.hour!=1)]=np.nan
    return out

def prepare_era5():
    inv=pd.read_csv(ROOT/'metadata/core_download_inventory.csv')
    parts={};source_audit=[]
    for rel in sorted(inv.file.unique()):
        path=ROOT/rel
        expected=inv.loc[inv.file.eq(rel),'sha256'].iloc[0]
        if sha256(path)!=expected: raise ValueError(f'Hash mismatch: {rel}')
        with xr.open_dataset(path) as ds:
            ds=ds.load()
            if 'valid_time' in ds: ds=ds.rename({'valid_time':'time'})
            # ARCO and CDS encode the same 0.1-degree grid with different float
            # precision. Canonicalize labels before xarray alignment; never
            # interpolate a spatial field to fix a coordinate-label mismatch.
            ds=ds.assign_coords(latitude=np.round(ds.latitude.values,6),
                                longitude=np.round(ds.longitude.values,6))
            for var in ds.data_vars:
                parts.setdefault(var,[]).append(ds[var])
    combined={}
    for var,arrays in parts.items():
        a=xr.concat(arrays,dim='time').sortby('time')
        if pd.DatetimeIndex(a.time.values).duplicated().any():raise ValueError(f'Duplicate ERA5 {var}')
        before=int(a.isnull().sum())
        if var in ['ssr','str','sshf','slhf']:
            dt=pd.DatetimeIndex(a.time.values)
            delta=a-a.shift(time=1)
            delta=xr.where(a.time.dt.hour==1,a,delta)
            contiguous=np.r_[False,(dt[1:]-dt[:-1])==pd.Timedelta(hours=1)]
            keep=xr.DataArray(contiguous|(dt.hour==1),dims='time',coords={'time':a.time})
            a=delta.where(keep)
        if var in ['t2m','d2m','skt']: a=a-273.15
        elif var=='tp': a=a*1000
        elif var in ['ssrd','strd','ssr','str','sshf','slhf']: a=a/3600
        a.attrs={'units':'degC' if var in ['t2m','d2m','skt'] else 'mm/hour_interval' if var=='tp'
                 else 'W/m2' if var in ['ssrd','strd','ssr','str','sshf','slhf'] else 'Pa' if var=='sp' else 'm/s'}
        combined[var]=a
        source_audit.append(dict(variable=var,source_missing=before,processed_missing=int(a.isnull().sum()),
          conversion='deaccumulate_then_J_per_hour_to_W' if var in ['ssr','str','sshf','slhf'] else
          'ARCO_hourly_increment_no_difference' if var in ['tp','ssrd','strd'] else 'instantaneous'))
    ds=xr.Dataset(combined)
    ds.attrs={'time_standard':'UTC','energy_flux_sign':'ECMWF positive downward; H and LE negated only in source feature extraction',
              'source_files':'metadata/core_download_inventory.csv'}
    ds.to_netcdf(INPUT/'era5_hourly.nc')
    csv_dump(pd.DataFrame(source_audit),TABLES/'era5_conversion_audit.csv')
    # Reference glacier centroid, defined by the provided geometry, not event anomalies.
    with xr.open_dataset(ROOT/'data/raw/era5_land/reference_geometry/attachment4_glacier_reference.nc') as g:
        mask=np.isfinite(g.glacier_mask.values)
        xx,yy=np.meshgrid(g.x.values,g.y.values)
        x=float(xx[mask].mean());y=float(yy[mask].mean())
        lon,lat=Transformer.from_crs(32645,4326,always_xy=True).transform(x,y)
    lats=sorted(ds.latitude.values);lons=sorted(ds.longitude.values)
    plat=float(min(lats,key=lambda v:abs(v-lat)));plon=float(min(lons,key=lambda v:abs(v-lon)))
    near_lat=sorted(lats,key=lambda v:abs(v-lat))[:2];near_lon=sorted(lons,key=lambda v:abs(v-lon))[:2]
    cells=[(float(a),float(b)) for a in near_lat for b in near_lon]
    with xr.open_dataset(ROOT/'data/raw/era5_land/reference_geometry/attachment4_glacier_reference.nc') as g:
        reference_elevation=float(np.nanmedian(g.dem.values[mask]))
    with xr.open_dataset(INPUT/'model_grid_static_reference.nc') as static:
        model_height=float(static.model_orography_m.sel(latitude=plat,longitude=plon,method='nearest'))
        glacier_fraction=float(static.model_glacier_fraction.sel(latitude=plat,longitude=plon,method='nearest'))
    spatial={'reference_centroid':{'latitude':lat,'longitude':lon},'primary_cell':[plat,plon],
      'neighbors_2x2':cells,'station':[CFG['station_latitude'],CFG['station_longitude']],
      'reference_glacier_median_elevation_m':reference_elevation,'model_primary_elevation_m':model_height,
      'model_primary_glacier_fraction':glacier_fraction,
      'station_in_download_domain':False,'geometry_role':'provided glacier reference; not verified release polygon'}
    json_dump(ROOT/'metadata/spatial_selection.json',spatial)
    return ds,spatial

def extract_source(ds,spatial,selection='primary'):
    if selection=='primary': chosen=ds.sel(latitude=spatial['primary_cell'][0],longitude=spatial['primary_cell'][1],method='nearest')
    elif selection=='mean4':
        cells=[ds.sel(latitude=a,longitude=b,method='nearest') for a,b in spatial['neighbors_2x2']]
        chosen=xr.concat(cells,dim='cell').mean('cell',skipna=False)
    elif selection=='median4':
        cells=[ds.sel(latitude=a,longitude=b,method='nearest') for a,b in spatial['neighbors_2x2']]
        chosen=xr.concat(cells,dim='cell').median('cell',skipna=False)
    else:
        a,b=map(float,selection.split(','));chosen=ds.sel(latitude=a,longitude=b,method='nearest')
    d=chosen.to_dataframe()[list(ds.data_vars)]
    t=d.t2m;td=d.d2m
    # Magnus relative humidity over water, fixed convention for air RH comparisons.
    rh=100*np.exp(17.625*td/(243.04+td)-17.625*t/(243.04+t))
    rh=rh.clip(0,100)
    out=pd.DataFrame(dict(T2=t,P=d.tp,U10=np.hypot(d.u10,d.v10),RH2=rh,
           Rn=d.ssr+d.str,LWnet=d.str,H=-d.sshf,LE=-d.slhf,Ts=d.skt,
           Rsd=d.ssrd,Rld=d.strd,pressure=d.sp/100),index=d.index)
    out.index.name='time_utc'
    return out

def station_process(d):
    out=pd.DataFrame(index=d.index)
    for k,c in [('T2','met__ta_2m'),('P','met__precip'),('U10','met__ws_10m'),('RH2','met__rh_2m'),
                ('H','flux__h'),('LE','flux__le'),('VWC01','soil__vwc_0p1m'),('TKE','flux__tke'),('USTAR','flux__ustar')]:out[k]=d[c]
    rad=d[['radm__rsd','radm__rsu','radm__rld','radm__rlu']]
    out['Rn']=(rad.iloc[:,0]-rad.iloc[:,1]+rad.iloc[:,2]-rad.iloc[:,3]).where(rad.notna().all(axis=1))
    out['LWnet']=(rad.iloc[:,2]-rad.iloc[:,3]).where(rad.iloc[:,2:].notna().all(axis=1))
    out['GT']=(d.met__ta_20m-d.met__ta_2m)/18
    wd1=np.deg2rad(d.met__wd_2m);wd2=np.deg2rad(d.met__wd_20m)
    du=(-d.met__ws_20m*np.sin(wd2)+d.met__ws_2m*np.sin(wd1))/18
    dv=(-d.met__ws_20m*np.cos(wd2)+d.met__ws_2m*np.cos(wd1))/18
    out['vector_shear']=np.hypot(du,dv)
    for h in [1,2,4,10,20]:
        for typ,code in [('T','ta'),('RH','rh'),('U','ws')]:out[f'{typ}_{h}m']=d[f'met__{code}_{h}m']
    for dep in ['0p1','0p2','0p4','0p8','1p6']:
        out[f'soilT_{dep}']=d[f'soil__soilt_{dep}m'];out[f'VWC_{dep}']=d[f'soil__vwc_{dep}m']
    return out

def main():
    s,q=prepare_station();ds,sp=prepare_era5()
    d=station_process(station_view(s,q));src=extract_source(ds,sp)
    csv_dump(d,INPUT/'station_process.csv.gz',True);csv_dump(src,INPUT/'source_process.csv.gz',True)
    json_dump(TABLES/'input_summary.json',dict(station_rows=len(s),station_variables=len(s.columns),
      station_start=str(s.index.min()),station_end=str(s.index.max()),era5_hours=int(ds.sizes['time']),
      era5_variables=len(ds.data_vars),spatial=sp,main_qc=CFG['primary_qc']))
    print('Prepared copied raw observations and ERA5, no interpolation.',flush=True)

if __name__=='__main__':main()
