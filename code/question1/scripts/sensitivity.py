"""Predeclared one-dimension-at-a-time sensitivity runs; retain every result."""
import json
import numpy as np
import pandas as pd
import xarray as xr
from common import CFG,ROOT,INPUT,TABLES,read_frame,csv_dump,json_dump
from prepare import station_view,station_process,extract_source
from features import build_features
from ranking import evaluate

def main():
    base=read_frame(INPUT/'station_base.csv.gz');qc=read_frame(INPUT/'station_qc.csv.gz')
    main_features=read_frame(INPUT/'features_hourly.csv.gz')
    spatial=json.loads((ROOT/'metadata/spatial_selection.json').read_text(encoding='utf-8'))
    ds=xr.open_dataset(INPUT/'era5_hourly.nc').load()
    specs=[dict(name='main'),dict(name='season_7d',half=7),dict(name='season_30d',half=30),
      dict(name='cutoff_minus1h',offset=-1),dict(name='cutoff_minus3h',offset=-3),
      dict(name='timestamp_end',label='end'),dict(name='QC_0_and_4',policy='qc04'),
      dict(name='QC_0_1_4_9',policy='qc0149'),dict(name='coverage80',coverage=.8),
      dict(name='coverage100',coverage=1.),dict(name='flux_physical_review',flux_strict=True),
      dict(name='radiation_no_extra_review',review=False),
      dict(name='source_mean4',selection='mean4'),dict(name='source_median4',selection='median4'),
      dict(name='station_only',scope='station'),dict(name='source_only',scope='source')]
    for y in CFG['historical_years']:specs.append(dict(name=f'exclude_year_{y}',years=[a for a in CFG['historical_years'] if a!=y]))
    for lat,lon in spatial['neighbors_2x2']:
        if [lat,lon]!=spatial['primary_cell']:
            specs.append(dict(name=f'cell_{lat}_{lon}',selection=f'{lat},{lon}'))
    source_main=extract_source(ds,spatial)
    rows=[];foldrows=[]
    for spec in specs:
        settings=any(k in spec for k in ['policy','label','coverage','flux_strict','review','selection'])
        if settings:
            s=station_process(station_view(base,qc,policy=spec.get('policy','qc0'),
                review=spec.get('review',True),flux_strict=spec.get('flux_strict',False),label=spec.get('label','start')))
            source=extract_source(ds,spatial,spec['selection']) if 'selection' in spec else source_main
            f,_=build_features(s,source,spec.get('coverage',.9))
        else:f=main_features
        cutoff=pd.Timestamp(CFG['main_cutoff_utc'])+pd.Timedelta(hours=spec.get('offset',0))
        r,folds,_,_=evaluate(f,half=spec.get('half',15),years=spec.get('years'),cutoff=cutoff,
                          scope=spec.get('scope','combined'),pseudo=False)
        r['scenario']=spec['name'];r['same_candidate_scope']=spec.get('scope','combined')=='combined'
        rows.append(r);folds['scenario']=spec['name'];foldrows.append(folds)
        print('Sensitivity:',spec['name'],','.join(r.loc[r.selected_top5,'group']),flush=True)
    out=pd.concat(rows,ignore_index=True);csv_dump(out,TABLES/'sensitivity_rankings.csv')
    csv_dump(pd.concat(foldrows,ignore_index=True),TABLES/'sensitivity_fold_rankings.csv')
    same=out[out.same_candidate_scope]
    stability=same.groupby(['group','factor']).agg(scenarios=('scenario','size'),
       evaluable_scenarios=('eligible','sum'),selected_count=('selected_top5','sum'),
       selection_frequency_all=('selected_top5','mean'),median_rank=('rank','median'),
       minimum_rank=('rank','min'),maximum_rank=('rank','max')).reset_index()
    csv_dump(stability,TABLES/'robustness_summary.csv')
    json_dump(ROOT/'metadata/sensitivity_scenarios.json',specs)

if __name__=='__main__':main()
