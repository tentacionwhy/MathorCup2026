"""Verify copied inputs, full outputs, plausible units and portable code paths."""
import json
import re
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import xarray as xr
from common import ROOT,TABLES,INPUT,CFG,CATALOG,sha256,json_dump,read_frame

def main():
    checks={}
    manifest=json.loads((ROOT/'metadata/input_manifest.json').read_text(encoding='utf-8'))
    for r in manifest:
        p=ROOT/r['path']
        if not p.is_file() or sha256(p)!=r['sha256']:raise AssertionError('Input missing/changed: '+r['path'])
    checks['copied_input_hashes']=len(manifest)
    catalog=pd.read_csv(TABLES/'feature_catalog.csv');assert len(catalog)==31
    checks['candidate_columns']=len(catalog)
    evidence=pd.read_csv(TABLES/'anomaly_evidence.csv');assert len(evidence)==31
    assert evidence.event_value.notna().all(),evidence[evidence.event_value.isna()].feature.tolist()
    checks['all_31_event_values_computed']=True
    f=read_frame(INPUT/'features_hourly.csv.gz');assert f.index.is_unique
    assert f.columns.tolist()==CATALOG.feature.tolist()
    hist=pd.read_csv(TABLES/'matched_anchors.csv');assert len(hist)==155
    checks['nominal_anchors']=155
    rank=pd.read_csv(TABLES/'group_rankings.csv');assert len(rank)==10
    top=pd.read_csv(TABLES/'top5_evidence.csv');assert len(top)==5 and top.group.nunique()==5
    assert top.valid_folds.ge(6).all()
    checks['five_unique_evaluable_groups']=top.group.tolist()
    assert top.median_q.between(0,1).all()
    with xr.open_dataset(INPUT/'era5_hourly.nc') as ds:
        assert dict(ds.sizes)=={'time':12528,'latitude':5,'longitude':6},dict(ds.sizes)
        for v in ['tp','t2m','ssr','str','sshf','slhf']:assert ds[v].notnull().any()
        # Independent conservation check against original daily cumulative delivery.
        raw_path=ROOT/'data/raw/era5_land/net_flux/source_net_flux_2026_0708.nc'
        with xr.open_dataset(raw_path) as raw:
            raw=raw.assign_coords(latitude=np.round(raw.latitude.values,6),longitude=np.round(raw.longitude.values,6))
            raw=raw.sel(latitude=ds.latitude,longitude=ds.longitude)
            for var in ['ssr','str','sshf','slhf']:
                observed=raw[var].sel(valid_time='2026-08-21 00:00').values
                rebuilt=(ds[var].sel(time=slice('2026-08-20 01:00','2026-08-21 00:00')).sum('time',skipna=False)*3600).values
                np.testing.assert_allclose(rebuilt,observed,rtol=3e-6,atol=5.)
    checks['four_ERA5_daily_energy_sums_match_original']=True
    checks['era5_coordinate_alignment']='5x6 verified; no artificial coordinate unions'
    # Independently recalculate event station mean from the copied raw CSV.
    raw_station=pd.read_csv(ROOT/'data/raw/hourly/MET/MET_Gyirong_2026.csv')
    raw_time=pd.to_datetime(raw_station.Timestamp,format='mixed')
    mask=(raw_time>='2026-08-25 10:00')&(raw_time<='2026-08-26 09:00')
    expected=raw_station.loc[mask,'Ta_2m(degree C)'].mean()
    got=evidence.loc[evidence.feature.eq('station__Tmean24'),'event_value'].iloc[0]
    np.testing.assert_allclose(got,expected,atol=1e-6,rtol=0)
    checks['station_24h_temperature_matches_raw_24_rows']=True
    for i in range(1,6):
        paths=list((ROOT/'results/figures').glob(f'fig3_{i}_*.pdf'));assert len(paths)==1
        assert paths[0].with_suffix('.svg').is_file() and paths[0].with_suffix('.png').is_file()
    checks['five_figure_export_sets']=True
    for p in list((ROOT/'scripts').glob('*.py'))+[ROOT/'run.py']:
        text=p.read_text(encoding='utf-8')
        assert not re.search(r"(?<![A-Za-z])[A-Za-z]:[\\/]",text),f'Absolute drive path in {p.name}'
    checks['code_uses_no_absolute_drive_paths']=True
    assert (ROOT/'manuscript/q1_section.tex').is_file()
    assert (ROOT/'reports/第一问完整结果.md').is_file()
    checks['protocol_and_numerical_report']=True
    pdf=ROOT/'manuscript/main.pdf'
    if pdf.exists():
        from pypdf import PdfReader
        reader=PdfReader(pdf);text='\n'.join(p.extract_text() for p in reader.pages)
        assert len(text)>3000
        checks['manuscript_pages']=len(reader.pages)
        checks['manuscript_text_extractable']=True
    json_dump(ROOT/'reports/verification.json',dict(status='passed',checks=checks))
    print(json.dumps(checks,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
