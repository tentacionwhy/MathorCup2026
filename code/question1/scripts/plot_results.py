"""Five manuscript figures; every quantitative panel has a CSV source."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import font_manager
from matplotlib.colors import ListedColormap
from common import ROOT,CFG,GROUPS,CATALOG,INPUT,TABLES,FIGURES,read_frame,json_dump

available={x.name for x in font_manager.fontManager.ttflist}
font=next((x for x in ['Microsoft YaHei','SimHei','Noto Sans CJK SC','Arial Unicode MS'] if x in available),'DejaVu Sans')
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':[font,'Arial','DejaVu Sans'],
  'font.size':7.5,'axes.titlesize':8.2,'axes.labelsize':7.5,'legend.fontsize':6.7,
  'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.65,'lines.linewidth':1.05,
    'axes.unicode_minus':False,'svg.fonttype':'none','pdf.fonttype':42,'figure.facecolor':'white','legend.frameon':False})
BLUE='#4477AA'; ORANGE='#CC8844'; DARK='#333333'; GRAY='#B7BEC5'; PALE='#DCE6F0'
cutoff=pd.Timestamp(CFG['main_cutoff_utc']);local_event=pd.Timestamp(CFG['event_local'])

def local(t):return pd.DatetimeIndex(t)+pd.Timedelta(hours=8)
def letter(ax,x):ax.text(-.08,1.06,x,transform=ax.transAxes,weight='bold',fontsize=9)
def save(fig,name,pdf=True):
    fig.savefig(FIGURES/f'{name}.png',dpi=250,facecolor='white')
    fig.savefig(FIGURES/f'{name}.svg',facecolor='white')
    if pdf:fig.savefig(FIGURES/f'{name}.pdf',facecolor='white')
    plt.close(fig)

def time_axis(ax,days=7):
    ax.axvline(local_event,color=DARK,lw=.8,ls='--',alpha=.65)
    ax.set_xlim(local_event-pd.Timedelta(days=days),local_event+pd.Timedelta(hours=1))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1 if days<=7 else 7))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax.grid(axis='y',color='#E5E8EB',lw=.5,zorder=0)

def main():
    station=read_frame(INPUT/'station_process.csv.gz');source=read_frame(INPUT/'source_process.csv.gz')
    s=station.loc[cutoff-pd.Timedelta(days=30):cutoff];src=source.loc[cutoff-pd.Timedelta(days=30):cutoff]
    profile=pd.read_csv(TABLES/'boundary_layer_profiles.csv')
    # 1: distinct vertical structure and temporal turbulence evidence.
    fig=plt.figure(figsize=(7.2,3.55),layout='constrained');gs=fig.add_gridspec(2,3,height_ratios=[1,1])
    axes=[fig.add_subplot(gs[0,i]) for i in range(3)]
    for ax,measure,title,unit,k in zip(axes,['T','RH','U'],['气温廓线','湿度廓线','风速廓线'],['气温 (°C)','相对湿度 (%)','风速 (m/s)'],'abc'):
        for period,ls,pname in [('early_4d','--','前7至3天'),('late_3d','-','最后3天')]:
            for clock,color,cname in [('day',ORANGE,'昼'),('night',BLUE,'夜')]:
                z=profile[(profile.measure==measure)&(profile.period==period)&(profile.clock==clock)]
                ax.plot(z['mean'],z.height_m,ls=ls,color=color,marker='o',ms=2,label=pname+cname)
        ax.set(xlabel=unit,ylabel='距地高度 (m)',title=title,yticks=[1,4,10,20]);letter(ax,k)
    axes[0].legend(ncol=2,fontsize=5.6,loc='best',handlelength=1.5,columnspacing=.6)
    ax=fig.add_subplot(gs[1,0]);z=s.loc[cutoff-pd.Timedelta(days=7):]
    ax.plot(local(z.index),z.GT,color=BLUE,label='2–20 m温度梯度')
    ax.axhline(0,color=GRAY,lw=.7);ax.set(ylabel='温度梯度 (°C/m)',title='近地层分层');time_axis(ax);ax.xaxis.set_major_locator(mdates.DayLocator(interval=3));letter(ax,'d')
    ax=fig.add_subplot(gs[1,1]);ax.plot(local(z.index),z.vector_shear,color=BLUE)
    ax.set(ylabel=r'矢量风切变 ($s^{-1}$)',title='2–20 m矢量风切变');time_axis(ax);ax.xaxis.set_major_locator(mdates.DayLocator(interval=3));letter(ax,'e')
    ax=fig.add_subplot(gs[1,2]);ax.plot(local(z.index),z.TKE,color=ORANGE)
    ax.set(ylabel='TKE (m²/s²)',title='湍流动能');time_axis(ax);ax.xaxis.set_major_locator(mdates.DayLocator(interval=3));letter(ax,'f')
    save(fig,'fig3_1_boundary_layer')
    # 2: temperature and energy over 30 days, without matching absolute temperatures.
    fig,axs=plt.subplots(2,2,figsize=(7.2,3.6),layout='constrained')
    for ax,c,title,unit,k in zip(axs.flat,['T2','Rn','H','LE'],['气温','净辐射','感热交换','潜热交换'],['°C','W/m²','W/m²','W/m²'],'abcd'):
        ax.plot(local(s.index),s[c].rolling(6,min_periods=6).mean(),color=BLUE,label='本站')
        ax.plot(local(src.index),src[c].rolling(6,min_periods=6).mean(),color=ORANGE,label='源区ERA5')
        ax.set(title=title+'（6h均值）',ylabel=unit);time_axis(ax,30);letter(ax,k)
    axs[0,0].legend(ncol=2,loc='upper left')
    save(fig,'fig3_2_energy_process')
    # 3: separate precipitation, RH and soil responses.
    fig,axs=plt.subplots(2,2,figsize=(7.2,3.6),layout='constrained')
    z=s.loc[cutoff-pd.Timedelta(days=7):];zz=src.loc[cutoff-pd.Timedelta(days=7):]
    ax=axs[0,0];ax.step(local(zz.index),zz.P,where='post',color=ORANGE,label='源区ERA5')
    ax.plot(local(z.index),z.P,color=BLUE,label='本站');ax.set(title='小时降水',ylabel='mm');ax.legend(ncol=2)
    ax=axs[0,1]
    for d,color,label in [(z,BLUE,'本站'),(zz,ORANGE,'源区ERA5')]:ax.plot(local(d.index),d.RH2.rolling(6,min_periods=6).mean(),color=color,label=label)
    ax.set(title='近地面湿度（6h均值）',ylabel='相对湿度 (%)')
    ax=axs[1,0]
    for dep,color,label in [('0p1',BLUE,'0.1 m'),('0p4',ORANGE,'0.4 m'),('0p8','#228833','0.8 m')]:ax.plot(local(z.index),z['VWC_'+dep],color=color,label=label)
    ax.set(title='本站土壤湿润响应',ylabel='体积含水量 (m³/m³)');ax.legend(ncol=3,fontsize=6)
    ax=axs[1,1]
    for dep,color,label in [('0p1',BLUE,'0.1 m'),('0p8',ORANGE,'0.8 m')]:ax.plot(local(z.index),z['soilT_'+dep],color=color,label=label)
    ax.set(title='本站土壤热响应',ylabel='土温 (°C)');ax.legend(ncol=2)
    for ax,k in zip(axs.flat,'abcd'):time_axis(ax);letter(ax,k)
    save(fig,'fig3_3_water_process')
    # 4: four key factors against empirical matched-season envelopes.
    env=pd.read_csv(TABLES/'historical_envelopes.csv',parse_dates=['time_utc'])
    fig,axs=plt.subplots(2,2,figsize=(7.2,3.6),layout='constrained')
    names=['station__Tmean24','station__dVWC24','source__LEmean24','source__RHmean24']
    labels=['本站24h均温','本站24h浅层含水量变化','源区24h潜热交换','源区24h相对湿度']
    units=['°C','m³/m³','W/m²','%']
    for ax,c,title,unit,k in zip(axs.flat,names,labels,units,'abcd'):
        z=env[env.feature==c];t=local(z.time_utc)
        ax.fill_between(t,z.q05,z.q95,color=PALE,label='历史5%–95%')
        ax.plot(t,z['median'],color=GRAY,lw=.8,label='历史中位数')
        ax.plot(t,z.value,color=BLUE,label='2026事件前')
        ax.set(title=title,ylabel=unit);time_axis(ax);letter(ax,k)
    axs[0,0].legend(ncol=3,fontsize=5.8,handlelength=1.2,columnspacing=.6,loc='upper left')
    save(fig,'fig3_4_historical_anomalies')
    # 5: numerical ranks and full-setting stability, with unavailable groups visible.
    ranks=pd.read_csv(TABLES/'group_rankings.csv');sens=pd.read_csv(TABLES/'sensitivity_rankings.csv')
    fig,(ax,hm)=plt.subplots(1,2,figsize=(7.2,3.35),gridspec_kw={'width_ratios':[1,1.4]},layout='constrained')
    order=ranks.group.tolist();y=np.arange(len(order));scores=-np.log10(ranks.median_q)
    colors=[BLUE if v else GRAY for v in ranks.selected_top5]
    ax.barh(y,scores.fillna(0),color=colors,height=.66)
    for i,r in ranks.iterrows():
        ax.text((scores.iloc[i] if np.isfinite(scores.iloc[i]) else 0)+.015,i,
                f'Q={r.median_q:.3f}' if np.isfinite(r.median_q) else '历史支持不足',va='center',fontsize=6)
    ax.set(yticks=y,yticklabels=[f'{g} {GROUPS[g]}' for g in order],xlabel=r'$-\log_{10}(Q)$（校准尾部比例中位数）',title='因素组异常证据初排')
    ax.invert_yaxis();ax.set_xlim(0,max(scores.max(),.5)+.38);letter(ax,'a')
    subset=sens[sens.same_candidate_scope]
    matrix=subset.pivot(index='group',columns='scenario',values='rank').reindex(order)
    im=hm.imshow(np.ma.masked_invalid(matrix.values),aspect='auto',cmap='Blues_r',vmin=1,vmax=10,interpolation='nearest')
    hm.set(yticks=y,yticklabels=order,xticks=np.arange(len(matrix.columns)),
      xticklabels=[str(i+1) for i in range(len(matrix.columns))],title='设置变化下的因素名次',xlabel='敏感性设置编号（详见CSV）')
    hm.tick_params(axis='x',labelsize=5.5);letter(hm,'b');cb=fig.colorbar(im,ax=hm,fraction=.04,pad=.02);cb.set_label('名次',fontsize=6)
    save(fig,'fig3_5_ranking_stability')
    # Supplementary diagnostic, not another manuscript PDF.
    diag=pd.read_csv(TABLES/'pseudo_event_diagnostics.csv')
    fig,ax=plt.subplots(figsize=(5.8,2.5),layout='constrained')
    ax.hist(diag.margin,bins=24,color=BLUE,alpha=.8)
    ax.axvline(0,color=ORANGE,ls='--',lw=1.3)
    ax.set(xlabel='伪事件前五分数和 − 同校准集下真实事件分数和',ylabel='比较次数',title='留块伪事件诊断（相关比较，非独立样本p值）')
    ax.text(.02,.95,f'n={len(diag)}；伪事件不低于真实事件：{diag.pseudo_exceeds_event.mean():.1%}',transform=ax.transAxes,va='top',fontsize=8)
    save(fig,'supp_pseudo_event_diagnostic',pdf=False)
    contracts=[]
    for name,claim,sourcefiles in [
      ('fig3_1_boundary_layer','近地层具有昼夜分层和随时间变化的湍流状态；不代表完整边界层', ['boundary_layer_profiles.csv','station_process.csv.gz']),
      ('fig3_2_energy_process','本站和源区天气与能量过程随时间变化，绝对值不作同址校验',['station_process.csv.gz','source_process.csv.gz']),
      ('fig3_3_water_process','本站与源区降水不同，本站土壤呈独立陆面响应',['process_observations.csv','station_process.csv.gz','source_process.csv.gz']),
      ('fig3_4_historical_anomalies','代表指标中异常强度与持续性不相同，不能都称极端天气',['historical_envelopes.csv']),
      ('fig3_5_ranking_stability','前五为相对排序，部分因素及湍流可评估性对设置敏感',['group_rankings.csv','sensitivity_rankings.csv'])]:
        contracts.append(dict(name=name,claim=claim,archetype='quantitative grid',source_data=sourcefiles,
            backend='Python/matplotlib',width_mm=183,statistics='empirical historical percentiles / correlated split variability, no causal p-values',
            export='PDF and editable-text SVG, PNG preview',image_integrity='no selective pixel manipulation'))
    json_dump(ROOT/'metadata/figure_contracts.json',contracts)
    print('Exported five figures in PDF, editable SVG and PNG; supplementary diagnostic.',flush=True)

if __name__=='__main__':main()
