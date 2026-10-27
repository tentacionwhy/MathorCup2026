"""Shared project paths, schema and deterministic I/O. No external data paths."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / 'config/analysis.json').read_text(encoding='utf-8-sig'))
TABLES = ROOT / 'results/tables'
FIGURES = ROOT / 'results/figures'
INPUT = ROOT / 'data/input'
for _p in (TABLES, FIGURES, INPUT, ROOT/'reports', ROOT/'logs', ROOT/'tmp'):
    _p.mkdir(parents=True, exist_ok=True)
GROUPS = {
 'G1':'温度状态与变化', 'G2':'前期降水', 'G3':'辐射条件',
 'G4':'感热交换', 'G5':'潜热交换', 'G6':'风场',
 'G7':'空气湿度', 'G8':'土壤湿润', 'G9':'近地层热力分层', 'G10':'湍流强度'}
GROUP_INDICATORS={
 'G1':'24h均温、相邻24h温差','G2':'24/72/168h累计降水',
 'G3':'24/72h净辐射能、24h净长波','G4':'24h平均感热通量',
 'G5':'24h平均潜热通量','G6':'6h均风、24h最大小时风速',
 'G7':'24h平均相对湿度','G8':'24h浅层含水量及端点变化',
 'G9':'6h平均2—20m温度梯度','G10':'6h平均TKE及摩擦速度'}
GROUP_VIEWS={
 'G1':'过程、极端性','G2':'过程、极端性','G3':'过程、极端性',
 'G4':'交换、过程','G5':'交换、过程','G6':'结构、过程、极端性',
 'G7':'结构、过程','G8':'陆面响应','G9':'结构','G10':'结构'}

def json_dump(path, obj):
    def convert(x):
        if isinstance(x, (np.integer,)): return int(x)
        if isinstance(x, (np.floating,)): return float(x) if np.isfinite(x) else None
        if isinstance(x, np.ndarray): return x.tolist()
        if isinstance(x, (pd.Timestamp, Path)): return str(x)
        raise TypeError(type(x).__name__)
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=convert), encoding='utf-8')

def csv_dump(frame, path, index=False):
    frame.to_csv(path, index=index, encoding='utf-8-sig', float_format='%.9g',
                 date_format='%Y-%m-%d %H:%M:%S')

def read_frame(path):
    return pd.read_csv(path, index_col=0, parse_dates=[0])

def sha256(path):
    h=hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def feature_catalog():
    rows=[]
    def add(key, family, group, label, unit, window, op, inputs, tail='two', source=True):
        for loc in (['station','source'] if source else ['station']):
            rows.append(dict(feature=f'{loc}__{key}', indicator=family, group=group,
              factor=GROUPS[group], label=label, location=loc, unit=unit, window_h=window,
              operation=op, inputs=inputs, tail=tail,
              definition=f'{op}; w={window}h; {inputs}',
              quality_rule='full' if op in ['sum','energy','max'] else
                 ('both_endpoints' if op=='endpoint_diff' else 'mean_coverage_and_no_empty_6h_block')))
    add('Tmean24','M01','G1','24h平均气温','degC',24,'mean','T2')
    add('dT24','M02','G1','相邻24h均温变化','degC',24,'block_diff','T2')
    for w in [24,72,168]: add(f'Rain{w}','M03','G2',f'{w}h累计降水','mm',w,'sum','P','upper')
    for w in [24,72]: add(f'RnEnergy{w}','M04','G3',f'{w}h净辐射能量','MJ/m2',w,'energy','Rn')
    add('LWmean24','M05','G3','24h平均净长波','W/m2',24,'mean','LWnet')
    add('Hmean24','M06','G4','24h平均感热通量','W/m2',24,'mean','H')
    add('LEmean24','M07','G5','24h平均潜热通量','W/m2',24,'mean','LE')
    add('Umean6','M08','G6','6h平均10m风速','m/s',6,'mean','U10','upper')
    add('Umax24','M08','G6','24h最大小时风速','m/s',24,'max','U10','upper')
    add('RHmean24','M09','G7','24h平均2m相对湿度','%',24,'mean','RH2')
    add('VWCmean24','M10','G8','24h浅层含水量','m3/m3',24,'mean','VWC01',source=False)
    add('dVWC24','M11','G8','24h浅层含水量变化','m3/m3',24,'endpoint_diff','VWC01',source=False)
    add('GTmean6','M12','G9','6h平均2至20m温度梯度','degC/m',6,'mean','GT',source=False)
    add('TKEmean6','M13','G10','6h平均湍动能','m2/s2',6,'mean','TKE',source=False)
    add('USTARmean6','M14','G10','6h平均摩擦速度','m/s',6,'mean','USTAR',source=False)
    df=pd.DataFrame(rows)
    mapping_station={'T2':'MET:Ta_2m(degree C)','P':'MET:Precip(mm)',
      'U10':'MET:WS_10m(m/s)','RH2':'MET:RH_2m(%)',
      'Rn':'RADM:Rsd-Rsu+Rld-Rlu','LWnet':'RADM:Rld-Rlu',
      'H':'FLUX:H(W/m2)','LE':'FLUX:LE(W/m2)',
      'VWC01':'SOIL:VWC_0.1m(m3/m3)','GT':'MET:(Ta_20m-Ta_2m)/18',
      'TKE':'FLUX:TKE(m2/s2)','USTAR':'FLUX:USTAR(m/s)'}
    mapping_source={'T2':'ERA5:t2m-273.15','P':'ARCO:tp*1000; already hourly',
      'U10':'ERA5:sqrt(u10^2+v10^2)','RH2':'ERA5:100*exp(17.625*d2m/(243.04+d2m)-17.625*t2m/(243.04+t2m)); degC',
      'Rn':'CDS:hourly_deacc(ssr+str)/3600','LWnet':'CDS:hourly_deacc(str)/3600',
      'H':'CDS:-hourly_deacc(sshf)/3600','LE':'CDS:-hourly_deacc(slhf)/3600'}
    formulas={'mean':'sum(valid X in [t-w+1,t])/n_valid',
      'sum':'sum(X[t-w+1:t]); all w hours required',
      'energy':'0.0036*sum(Rn[t-w+1:t]); W/m2 to MJ/m2; complete',
      'max':'max(X[t-w+1:t]); complete',
      'block_diff':'mean(X[t-23:t])-mean(X[t-47:t-24])',
      'endpoint_diff':'X(t)-X(t-24h); both endpoints required'}
    df['raw_field_mapping']=[(mapping_station if loc=='station' else mapping_source)[key] for loc,key in zip(df.location,df.inputs)]
    df['formula']=[formulas[k] for k in df.operation]
    df['time_support']='UTC hourly ends; station main assumes original label=start'
    df['data_type']=df.location.map({'station':'tower_observation','source':'ERA5_Land_reanalysis'})
    df['research_views']=df.group.map(GROUP_VIEWS)
    assert len(df)==31 and df.location.value_counts().to_dict()=={'station':18,'source':13}
    return df

CATALOG=feature_catalog()

def anchors(half=15, years=None, cutoff=None):
    years=CFG['historical_years'] if years is None else years
    cutoff=pd.Timestamp(CFG['main_cutoff_utc'] if cutoff is None else cutoff)
    return pd.DatetimeIndex([pd.Timestamp(year=y,month=8,day=26,hour=cutoff.hour)+pd.Timedelta(days=d)
                            for y in years for d in range(-half,half+1)])
