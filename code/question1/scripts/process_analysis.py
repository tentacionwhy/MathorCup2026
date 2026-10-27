"""Boundary-layer profiles, temporal observations and historical envelopes."""
import numpy as np
import pandas as pd
from common import CFG,CATALOG,ROOT,INPUT,TABLES,read_frame,csv_dump,json_dump
import json
from ranking import equal_year_weights

def weighted_quantile(values,weights,quantiles):
    order=np.argsort(values);x=np.asarray(values)[order];w=np.asarray(weights)[order]
    q=(np.cumsum(w)-.5*w)/np.sum(w)
    return np.interp(quantiles,q,x)

def envelopes(data,targets,columns,half=15):
    rows=[]
    hist=data.loc[data.index.year.isin(CFG['historical_years'])]
    for t in targets:
        # Calendar matching is by month/day and clock time, with a fixed leap-safe year.
        center=pd.Timestamp(year=2001,month=t.month,day=t.day)
        cal=pd.DatetimeIndex([pd.Timestamp(year=2001,month=m,day=d) for m,d in zip(hist.index.month,hist.index.day)])
        mask=(np.abs((cal-center).days)<=half)&(hist.index.hour==t.hour)
        candidate=hist.loc[mask,columns]
        for c in columns:
            ref=candidate[c].dropna();v=data[c].get(t,np.nan)
            if len(ref):
                weights=equal_year_weights(ref.index);low,median,high=weighted_quantile(ref.values,weights,[.05,.5,.95])
                pct=100*np.sum(weights*((ref.values<v)+.5*(ref.values==v))) if np.isfinite(v) else np.nan
            else:low=median=high=pct=np.nan
            rows.append(dict(time_utc=t,feature=c,value=v,q05=low,median=median,q95=high,
                percentile=pct,n=len(ref),years=ref.index.year.nunique()))
    return pd.DataFrame(rows)

def longest_run(mask):
    best=cur=0
    for flag in np.asarray(mask,dtype=bool):
        cur=cur+1 if flag else 0;best=max(best,cur)
    return best

def main():
    station=read_frame(INPUT/'station_process.csv.gz');source=read_frame(INPUT/'source_process.csv.gz')
    f=read_frame(INPUT/'features_hourly.csv.gz');cutoff=pd.Timestamp(CFG['main_cutoff_utc'])
    targets=pd.date_range(cutoff-pd.Timedelta(hours=167),cutoff,freq='h')
    # Restrict historical inputs to Jul-Sep to avoid expensive irrelevant rows.
    seasonal=f.loc[f.index.month.isin([7,8,9])]
    env=envelopes(seasonal,targets,list(CATALOG.feature));csv_dump(env,TABLES/'historical_envelopes.csv')
    durations=[]
    for c,z in env.groupby('feature',sort=False):
        low=z.value.lt(z.q05)&z.value.notna();high=z.value.gt(z.q95)&z.value.notna();outside=low|high
        hit=z.loc[outside,'time_utc']
        durations.append(dict(feature=c,lookback_h=168,valid_h=int(z.value.notna().sum()),
          low_hours=int(low.sum()),high_hours=int(high.sum()),outside_hours=int(outside.sum()),
          longest_outside_h=longest_run(outside),longest_high_h=longest_run(high),longest_low_h=longest_run(low),
          first_outside_utc=str(hit.min()) if len(hit) else '',last_outside_utc=str(hit.max()) if len(hit) else ''))
    csv_dump(pd.DataFrame(durations),TABLES/'anomaly_durations.csv')
    # Profiles compare the last 72h and preceding four days, by fixed local clock bins.
    profiles=[]
    for period,lo,hi in [('early_4d',cutoff-pd.Timedelta(days=7),cutoff-pd.Timedelta(days=3)),
                         ('late_3d',cutoff-pd.Timedelta(days=3),cutoff)]:
        d=station.loc[(station.index>lo)&(station.index<=hi)]
        local_hour=(d.index+pd.Timedelta(hours=8)-pd.Timedelta(hours=1)).hour
        for clock,mask in [('day', (local_hour>=11)&(local_hour<=17)),('night',(local_hour>=0)&(local_hour<=6))]:
            for measure in ['T','RH','U']:
                for h in [1,2,4,10,20]:
                    s=d.loc[mask,f'{measure}_{h}m']
                    profiles.append(dict(period=period,clock=clock,measure=measure,height_m=h,n=int(s.notna().sum()),
                       mean=s.mean(),median=s.median(),q25=s.quantile(.25),q75=s.quantile(.75)))
    csv_dump(pd.DataFrame(profiles),TABLES/'boundary_layer_profiles.csv')
    # Structural diagnostics are descriptive, outside the frozen ranking pool.
    structure=[]
    for w in [168,72,24,6]:
        z=station.loc[(station.index>cutoff-pd.Timedelta(hours=w))&(station.index<=cutoff)]
        for c in ['GT','vector_shear','TKE','USTAR','H','LE','U10']:
            v=z[c]
            structure.append(dict(window_h=w,variable=c,n=int(v.notna().sum()),
                mean=v.mean(),minimum=v.min(),maximum=v.max()))
    csv_dump(pd.DataFrame(structure),TABLES/'boundary_layer_windows.csv')
    z=station.loc[(station.index>cutoff-pd.Timedelta(days=7))&(station.index<=cutoff)]
    relations=[]
    for c in ['GT','vector_shear','USTAR','H','LE','U10']:
        for lag in [0,3,6]:
            pair=pd.concat([z[c].shift(lag).rename('driver'),z.TKE.rename('TKE')],axis=1).dropna()
            relations.append(dict(variable=c,driver_leads_h=lag,n=len(pair),
                spearman_rho=pair.corr(method='spearman').iloc[0,1] if len(pair)>=48 else np.nan,
                scope='7d descriptive co-variation; autocorrelated and shared diurnal cycle; not ranking or causal evidence'))
    csv_dump(pd.DataFrame(relations),TABLES/'boundary_layer_covariation.csv')
    observations=[]
    for loc,d in [('station',station),('source',source)]:
        for w in [24,72,168,720]:
            z=d.loc[(d.index>cutoff-pd.Timedelta(hours=w))&(d.index<=cutoff)]
            for c in d:
                v=z[c]
                observations.append(dict(location=loc,window_h=w,variable=c,n=int(v.notna().sum()),
                  mean=v.mean(),minimum=v.min(),maximum=v.max(),sum_complete=v.sum() if v.notna().sum()==w else np.nan,
                  first=v.dropna().iloc[0] if v.notna().any() else np.nan,
                  last=v.dropna().iloc[-1] if v.notna().any() else np.nan))
    csv_dump(pd.DataFrame(observations),TABLES/'process_observations.csv')
    # Comparable factors: aligned timestamps and own historical percentile/shape.
    evidence=pd.read_csv(TABLES/'anomaly_evidence.csv');pairs=[]
    for c in CATALOG.loc[CATALOG.location.eq('source'),'feature']:
        key=c.split('__')[1];sc='station__'+key
        a=evidence[evidence.feature.eq(sc)].iloc[0];b=evidence[evidence.feature.eq(c)].iloc[0]
        same_hist=f.loc[(f.index.year<=2025)&(f.index.month==8)&(f.index.hour==cutoff.hour),[sc,c]].dropna()
        rho=same_hist.corr(method='spearman').iloc[0,1] if len(same_hist)>=15 else np.nan
        signed_comparable=not key.startswith(('Hmean','LEmean'))
        pairs.append(dict(indicator=key,group=a.group,station_value=a.event_value,source_value=b.event_value,
           station_percentile=a.percentile,source_percentile=b.percentile,
           same_direction=bool((a.percentile-50)*(b.percentile-50)>0) if signed_comparable else None,
           historical_rho=rho,historical_pairs=len(same_hist),
           note='different sites; station H/LE sign not supplier-verified' if not signed_comparable else 'different sites and supports; no collocated validation'))
    csv_dump(pd.DataFrame(pairs),TABLES/'spatial_evidence.csv')
    # Assemble final evidence without changing the numerical ranking.
    rank=pd.read_csv(TABLES/'group_rankings.csv');dur=pd.DataFrame(durations).set_index('feature')
    robust=pd.read_csv(TABLES/'robustness_summary.csv').set_index('group')
    top=rank.loc[rank.selected_top5].copy()
    top['outside_hours_7d']=[dur.loc[c,'outside_hours'] for c in top.representative]
    top['longest_outside_h']=[dur.loc[c,'longest_outside_h'] for c in top.representative]
    top['settings_top5_frequency']=[robust.loc[g,'selection_frequency_all'] for g in top.group]
    scopes={'G1':'温度背景和变化；不等于实际融化量','G2':'区域/格点水分输入；不等于源区局地实测',
       'G3':'地表辐射背景；不是冰面融化能量','G4':'地气感热交换背景；本站符号未核实',
       'G5':'蒸发相变交换背景；不是冰川实际融水','G6':'近地风场过程；小时最大不是阵风',
       'G7':'空气湿润程度；不能单独归因为供水','G8':'本站陆面湿润响应；不是冰川基底水压',
       'G9':'本站2至20m热力分层；不是完整边界层高度','G10':'本站湍流交换；不代表高位冰崖观测'}
    top['mechanism_scope']=[scopes[g] for g in top.group]
    spatial=json.loads((ROOT/'metadata/spatial_selection.json').read_text(encoding='utf-8'))
    top['spatial_representativeness']=[
      f"grid elevation {spatial['model_primary_elevation_m']:.0f}m; glacier fraction {spatial['model_primary_glacier_fraction']:.4f}; regional background only"
      if loc=='source' else 'remote tower regional evidence; not source-site measurement' for loc in top.location]
    top['evidence_strength']=['relative ranking; no causal identification']*len(top)
    csv_dump(top,TABLES/'top5_evidence.csv')
    print('Computed structure, process, 31-feature envelopes and bounded evidence.',flush=True)

if __name__=='__main__':main()
