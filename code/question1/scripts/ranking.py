"""Matched seasonal rarity, nested group selection calibration and pseudo-events.

No observations are labelled as confirmed non-disasters. All tail proportions
are empirical descriptive quantities, not independent-sample p-values.
"""
from __future__ import annotations
from collections import Counter
from itertools import combinations
import numpy as np
import pandas as pd
from common import CFG,GROUPS,CATALOG,TABLES,INPUT,ROOT,anchors,read_frame,csv_dump,json_dump

def equal_year_weights(index):
    years=pd.DatetimeIndex(index).year
    unique,counts=np.unique(years,return_counts=True)
    sizes=dict(zip(unique,counts))
    return np.array([1/(len(unique)*sizes[y]) for y in years])

def tail_proportion(reference,values,tail='two'):
    ref=reference.dropna()
    vals=np.atleast_1d(np.asarray(values,dtype=float))
    if len(ref)==0:return np.full(len(vals),np.nan)
    order=np.argsort(ref.values,kind='stable');rv=ref.values[order]
    w=equal_year_weights(ref.index)[order];cw=np.r_[0,np.cumsum(w)]
    left=np.searchsorted(rv,vals,side='left');right=np.searchsorted(rv,vals,side='right')
    n=len(rv)
    up=(1+n*(1-cw[left]))/(n+1)
    low=(1+n*cw[right])/(n+1)
    r=up if tail=='upper' else low if tail=='lower' else np.minimum(1,2*np.minimum(up,low))
    return np.where(np.isfinite(vals),np.clip(r,1/(n+1),1),np.nan)

def anomaly_scores(reference,query,columns):
    a=pd.DataFrame(index=query.index)
    for c in columns:
        tail=CATALOG.loc[CATALOG.feature.eq(c),'tail'].iloc[0]
        r=tail_proportion(reference[c],query[c].to_numpy(),tail)
        a[c]=-np.log10(r)
    return a

def valid_each_year(frame,years,min_n):
    return all(int(frame.loc[frame.index.year==y].notna().sum())>=min_n for y in years)

def max_and_representative(scores):
    complete=scores.notna().all(axis=1)
    maxima=scores.max(axis=1).where(complete)
    representatives=pd.Series('',index=scores.index,dtype=object)
    if complete.any():representatives.loc[complete]=scores.loc[complete].idxmax(axis=1)
    return maxima,representatives

def greedy_five(score, reps, reference, threshold=.9):
    """One per physical group; predeclared cross-group coupling review only."""
    order=sorted(score,key=lambda g:(-score[g],int(g[1:])))
    selected=[]; decisions=[]
    pairs={frozenset(x) for x in CFG['redundancy_pairs']}
    for g in order:
        drop=False
        for kept in selected:
            if frozenset([g,kept]) not in pairs:continue
            a,b=reps[g],reps[kept]
            z=reference[[a,b]].dropna()
            rho=z.corr(method='spearman').iloc[0,1] if len(z)>=15 else np.nan
            if np.isfinite(rho) and abs(rho)>=threshold:
                decisions.append(dict(excluded=g,retained=kept,rho=rho,
                  rule='predeclared coupled wind/turbulence or temperature/gradient pair'))
                drop=True;break
        if not drop:selected.append(g)
        if len(selected)==5:break
    return selected,decisions

def fold_models(features,half=15,years=None,cutoff=None,scope='combined'):
    years=CFG['historical_years'] if years is None else list(years)
    cutoff=pd.Timestamp(CFG['main_cutoff_utc'] if cutoff is None else cutoff)
    hist=features.reindex(anchors(half,years,cutoff))
    event=features.reindex([cutoff])
    nref=3 if len(years)==5 else max(2,len(years)-2)
    minimum=min(15,int(np.ceil((2*half+1)/2)))
    models=[];rows=[]
    pool=CATALOG if scope=='combined' else CATALOG[CATALOG.location.eq(scope)]
    for fi,ref_years in enumerate(combinations(years,nref),1):
        cal_years=[y for y in years if y not in ref_years]
        ref=hist.loc[hist.index.year.isin(ref_years)]
        cal=hist.loc[hist.index.year.isin(cal_years)]
        model=dict(fold=fi,reference=ref,calibration=cal,groups={})
        for g in GROUPS:
            cols=[]
            for c in pool.loc[pool.group.eq(g),'feature']:
                if (np.isfinite(event[c].iloc[0]) and valid_each_year(ref[c],ref_years,minimum)
                    and valid_each_year(cal[c],cal_years,minimum)):
                    cols.append(c)
            base=dict(fold=fi,group=g,factor=GROUPS[g],reference_years=','.join(map(str,ref_years)),
              calibration_years=','.join(map(str,cal_years)),minimum_per_year=minimum)
            if not cols:
                rows.append({**base,'status':'no_common_eligible_feature'});continue
            ar=anomaly_scores(ref,ref,cols);ac=anomaly_scores(ref,cal,cols);ae=anomaly_scores(ref,event,cols)
            mc,rc=max_and_representative(ac);me,re=max_and_representative(ae)
            if not valid_each_year(mc,cal_years,minimum):
                rows.append({**base,'status':'insufficient_joint_calibration','eligible_columns':'|'.join(cols)});continue
            q=tail_proportion(mc,[me.iloc[0]],'upper')[0]
            rep=re.iloc[0]
            model['groups'][g]=dict(columns=cols,calibration_scores=mc,calibration_reps=rc,
                event_score=float(me.iloc[0]),event_rep=rep,event_q=float(q),
                calibration_anomaly=ac,reference_anomaly=ar)
            rows.append({**base,'status':'ok','q':q,'score':-np.log10(q),'representative':rep,
               'event_max_anomaly':me.iloc[0],'reference_n':int(ref[rep].notna().sum()),
               'calibration_n':int(mc.notna().sum()),'eligible_columns':'|'.join(cols)})
        models.append(model)
    folds=pd.DataFrame(rows)
    folds['selected_top5']=False;folds['ordinal_rank']=np.nan
    for model in models:
        ok=model['groups'];scores={g:-np.log10(v['event_q']) for g,v in ok.items()}
        reps={g:v['event_rep'] for g,v in ok.items()}
        chosen,_=greedy_five(scores,reps,model['reference'])
        for rank,g in enumerate(sorted(scores,key=lambda g:(-scores[g],int(g[1:]))),1):
            folds.loc[(folds.fold==model['fold'])&folds.group.eq(g),'ordinal_rank']=rank
        folds.loc[(folds.fold==model['fold'])&folds.group.isin(chosen),'selected_top5']=True
    return models,folds,hist,event

def summarize_folds(models,folds,hist,event):
    minimum=int(np.ceil(.6*len(models)));result=[]
    for g in GROUPS:
        z=folds.loc[folds.group.eq(g)&folds.status.eq('ok')]
        if len(z):
            reps=Counter(z.representative);rep=sorted(reps,key=lambda c:(-reps[c],c))[0]
            row=CATALOG.set_index('feature').loc[rep]
            rv=hist[rep].dropna();x=event[rep].iloc[0]
            weights=equal_year_weights(rv.index)
            percentile=100*np.sum(weights*((rv.to_numpy()<x)+.5*(rv.to_numpy()==x)))
            med=float(rv.median());mad=float(np.median(np.abs(rv-med)))
            result.append(dict(group=g,factor=GROUPS[g],representative=rep,label=row.label,
                location=row.location,unit=row.unit,window_h=int(row.window_h),event_value=x,
                historical_median=med,percentile=percentile,
                marginal_rarity=tail_proportion(rv,[x],row['tail'])[0],
                robust_z=(x-med)/(1.4826*mad) if mad>0 else np.nan,
                median_q=float(z.q.median()),median_score=float((-np.log10(z.q)).median()),
                q_min=float(z.q.min()),q_max=float(z.q.max()),valid_folds=len(z),total_folds=len(models),
                top5_frequency=float(z.selected_top5.mean()),representative_frequency=reps[rep]/len(z),
                eligible=len(z)>=minimum,historical_n=len(rv),historical_years=rv.index.year.nunique()))
        else: result.append(dict(group=g,factor=GROUPS[g],eligible=False,valid_folds=0,total_folds=len(models)))
    ranking=pd.DataFrame(result).sort_values(['eligible','median_q','top5_frequency','representative_frequency','group'],
             ascending=[False,True,False,False,True],na_position='last').reset_index(drop=True)
    ranking['rank']=np.arange(1,len(ranking)+1)
    ranking.loc[ranking.median_q.isna(),'rank']=np.nan
    ranking['selected_top5']=False;ranking['redundancy_note']=''
    pairs={frozenset(x) for x in CFG['redundancy_pairs']};chosen=[];decisions=[]
    for i,r in ranking.iterrows():
        if not r.get('eligible',False):continue
        blocked=False
        for j in chosen:
            prev=ranking.loc[j]
            if frozenset([r.group,prev.group]) not in pairs:continue
            xx=hist[[r.representative,prev.representative]].dropna()
            rho=xx.corr(method='spearman').iloc[0,1] if len(xx)>=15 else np.nan
            if np.isfinite(rho) and abs(rho)>=CFG['redundancy_threshold']:
                ranking.loc[i,'redundancy_note']=f'coupled_to_{prev.group}; rho={rho:.4f}'
                decisions.append(dict(excluded=r.group,retained=prev.group,rho=rho));blocked=True;break
        if not blocked:chosen.append(i)
        if len(chosen)==5:break
    ranking.loc[chosen,'selected_top5']=True
    ranking['selection_rank']=np.nan
    ranking.loc[chosen,'selection_rank']=np.arange(1,len(chosen)+1)
    return ranking,pd.DataFrame(decisions)

def full_feature_evidence(features,half=15,years=None,cutoff=None):
    cutoff=pd.Timestamp(CFG['main_cutoff_utc'] if cutoff is None else cutoff)
    hist=features.reindex(anchors(half,years,cutoff));out=[]
    for row in CATALOG.itertuples():
        r=hist[row.feature].dropna();x=features.loc[cutoff,row.feature]
        if len(r) and np.isfinite(x):
            w=equal_year_weights(r.index);p=100*np.sum(w*((r.values<x)+.5*(r.values==x)))
            q=tail_proportion(r,[x],row.tail)[0]
            out.append(dict(feature=row.feature,group=row.group,label=row.label,location=row.location,
              unit=row.unit,window_h=row.window_h,event_value=x,historical_median=r.median(),
              historical_q05=r.quantile(.05),historical_q95=r.quantile(.95),percentile=p,
              empirical_tail=q,anomaly_score=-np.log10(q),valid_n=len(r),valid_years=r.index.year.nunique(),
              tail=row.tail,direction='above' if x>r.median() else 'below' if x<r.median() else 'equal'))
        else:out.append(dict(feature=row.feature,group=row.group,label=row.label,location=row.location,
                             event_value=x,valid_n=len(r),status='unavailable'))
    return pd.DataFrame(out)

def pseudo_pipeline_diagnostics(models):
    records=[]
    for model in models:
        groups=model['groups'];cal=model['calibration'];ref=model['reference']
        for t in cal.index:
            year_start=cal.index[cal.index.year==t.year].min()
            block_start=year_start+pd.Timedelta(days=7*((t-year_start).days//7))
            # Exclude a held-out 7-day block plus guards for the maximum 168h window.
            lo=block_start-pd.Timedelta(hours=168);hi=block_start+pd.Timedelta(days=7,hours=168)
            scores_e={};scores_p={};reps_e={};reps_p={}
            min_cal=999999
            for g,m in groups.items():
                ps=m['calibration_scores'].get(t,np.nan)
                if not np.isfinite(ps):continue
                remaining=m['calibration_scores'].loc[(cal.index<lo)|(cal.index>=hi)].dropna()
                if len(remaining)<10:continue
                qe,qp=tail_proportion(remaining,[m['event_score'],ps],'upper')
                scores_e[g]=-np.log10(qe);scores_p[g]=-np.log10(qp)
                reps_e[g]=m['event_rep'];reps_p[g]=m['calibration_reps'].loc[t]
                min_cal=min(min_cal,len(remaining))
            if len(scores_e)<5:continue
            top_e,_=greedy_five(scores_e,reps_e,ref);top_p,_=greedy_five(scores_p,reps_p,ref)
            if len(top_e)<5 or len(top_p)<5:continue
            se=sum(scores_e[g] for g in top_e);sp=sum(scores_p[g] for g in top_p)
            records.append(dict(fold=model['fold'],pseudo_time_utc=str(t),groups_compared=len(scores_e),
               min_calibration_n=min_cal,event_top5_sum=se,pseudo_top5_sum=sp,
               margin=sp-se,pseudo_exceeds_event=sp>=se-1e-12,
               event_max=max(scores_e.values()),pseudo_max=max(scores_p.values())))
    return pd.DataFrame(records)

def evaluate(features,half=15,years=None,cutoff=None,scope='combined',pseudo=False):
    models,folds,hist,event=fold_models(features,half,years,cutoff,scope)
    ranking,decisions=summarize_folds(models,folds,hist,event)
    diag=pseudo_pipeline_diagnostics(models) if pseudo else pd.DataFrame()
    return ranking,folds,decisions,diag

def main():
    f=read_frame(INPUT/'features_hourly.csv.gz')
    r,folds,red,diag=evaluate(f,pseudo=True)
    csv_dump(r,TABLES/'group_rankings.csv');csv_dump(folds,TABLES/'fold_rankings.csv')
    csv_dump(full_feature_evidence(f),TABLES/'anomaly_evidence.csv')
    if red.empty:red=pd.DataFrame(columns=['excluded','retained','rho'])
    csv_dump(red,TABLES/'redundancy_decisions.csv');csv_dump(diag,TABLES/'pseudo_event_diagnostics.csv')
    hist=f.reindex(anchors());hist.index.name='anchor_utc';csv_dump(hist,TABLES/'matched_anchors.csv',True)
    csv_dump(hist.corr(method='spearman'),TABLES/'feature_spearman.csv',True)
    audit=[]
    for ga,gb in CFG['redundancy_pairs']:
        a=r.loc[r.group.eq(ga)].iloc[0];b=r.loc[r.group.eq(gb)].iloc[0]
        if pd.isna(a.representative) or pd.isna(b.representative):
            audit.append(dict(group_a=ga,group_b=gb,n=0,rho=np.nan,
              status='no jointly evaluable group representative',threshold=CFG['redundancy_threshold']))
        else:
            pair=hist[[a.representative,b.representative]].dropna()
            rho=pair.corr(method='spearman').iloc[0,1] if len(pair)>=15 else np.nan
            audit.append(dict(group_a=ga,group_b=gb,feature_a=a.representative,feature_b=b.representative,
              n=len(pair),rho=rho,threshold=CFG['redundancy_threshold'],
              status='below threshold; distinct physical groups retained' if np.isfinite(rho) and abs(rho)<CFG['redundancy_threshold']
                else 'threshold reached; refer to selection decisions'))
    csv_dump(pd.DataFrame(audit),TABLES/'redundancy_audit.csv')
    summary=dict(nominal_historical_anchors=len(hist),valid_folds=folds.status.value_counts().to_dict(),
      selected_groups=r.loc[r.selected_top5,'group'].tolist(),
      pseudo_comparisons=len(diag),pseudo_exceedance=float(diag.pseudo_exceeds_event.mean()) if len(diag) else None,
      pseudo_note='paired leave-block-out descriptive exceedance; correlated comparisons, not a p-value')
    json_dump(TABLES/'ranking_summary.json',summary)
    print(r[['rank','group','representative','event_value','median_q','valid_folds','selected_top5']].to_string(index=False),flush=True)
    print('Pseudo comparisons',len(diag),flush=True)

if __name__=='__main__':main()
