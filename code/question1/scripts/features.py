"""The complete predeclared 31-feature pool, plus support counts."""
import numpy as np
import pandas as pd
from common import ROOT,INPUT,TABLES,CATALOG,csv_dump,read_frame

def mean_roll(s,w,fraction):
    count=s.rolling(w,min_periods=1).count()
    out=s.rolling(w,min_periods=int(np.ceil(w*fraction))).mean()
    # No completely unobserved 6-hour sub-block in the window.
    block_ok=pd.Series(True,index=s.index)
    for shift in range(0,w,6):
        n=min(6,w-shift)
        block_ok &= s.notna().shift(shift,fill_value=False).rolling(n,min_periods=n).sum().gt(0)
    return out.where(block_ok),count

def build_features(station,source,fraction=.9):
    lo=min(station.index.min(),source.index.min());hi=max(station.index.max(),source.index.max())
    idx=pd.date_range(lo.floor('h'),hi.ceil('h'),freq='h',name='time_utc')
    inputs={'station':station.reindex(idx),'source':source.reindex(idx)}
    output=pd.DataFrame(index=idx);support=pd.DataFrame(index=idx)
    for row in CATALOG.itertuples():
        s=inputs[row.location][row.inputs];w=row.window_h
        if row.operation=='mean':v,n=mean_roll(s,w,fraction)
        elif row.operation=='block_diff':
            m,n=mean_roll(s,w,fraction);v=m-m.shift(w);n=n+n.shift(w)
        elif row.operation in ['sum','energy','max']:
            n=s.rolling(w,min_periods=1).count()
            v=s.rolling(w,min_periods=w).max() if row.operation=='max' else s.rolling(w,min_periods=w).sum()
            if row.operation=='energy':v=v*.0036
        elif row.operation=='endpoint_diff':v=s-s.shift(w);n=s.notna().astype(int)+s.shift(w).notna().astype(int)
        else:raise ValueError(row.operation)
        output[row.feature]=v;support[row.feature]=n
    assert output.shape[1]==31
    return output,support

def main():
    f,n=build_features(read_frame(INPUT/'station_process.csv.gz'),read_frame(INPUT/'source_process.csv.gz'))
    csv_dump(CATALOG,TABLES/'feature_catalog.csv')
    csv_dump(f,ROOT/'data/input/features_hourly.csv.gz',True)
    csv_dump(n,ROOT/'data/input/feature_support_hourly.csv.gz',True)
    print('Built all 31 predeclared features.',flush=True)

if __name__=='__main__':main()
