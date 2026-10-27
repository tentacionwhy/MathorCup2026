"""Generate a Chinese numerical report and the five-section LaTeX chapter."""
from pathlib import Path
import json
import shutil
import numpy as np
import pandas as pd
from common import ROOT,TABLES,GROUPS,GROUP_INDICATORS,GROUP_VIEWS,CATALOG,csv_dump,json_dump,CFG

def fmt(x,n=3):return f'{float(x):.{n}f}' if pd.notna(x) else '—'
def escape(s):
    for a,b in [('&',r'\&'),('%',r'\%'),('_',r'\_'),('#',r'\#')]:s=str(s).replace(a,b)
    return str(s)

def main():
    rank=pd.read_csv(TABLES/'group_rankings.csv');top=pd.read_csv(TABLES/'top5_evidence.csv')
    evidence=pd.read_csv(TABLES/'anomaly_evidence.csv').set_index('feature')
    obs=pd.read_csv(TABLES/'process_observations.csv')
    profile=pd.read_csv(TABLES/'boundary_layer_profiles.csv')
    summary=json.loads((TABLES/'ranking_summary.json').read_text(encoding='utf-8'))
    spatial=json.loads((ROOT/'metadata/spatial_selection.json').read_text(encoding='utf-8'))
    sens=pd.read_csv(TABLES/'robustness_summary.csv').set_index('group')
    duration=pd.read_csv(TABLES/'anomaly_durations.csv').set_index('feature')
    structure=pd.read_csv(TABLES/'boundary_layer_windows.csv')
    covariation=pd.read_csv(TABLES/'boundary_layer_covariation.csv')
    def b(var,w):return structure.loc[structure.variable.eq(var)&structure.window_h.eq(w),'mean'].iloc[0]
    def rho(var,lag=0):return covariation.loc[covariation.variable.eq(var)&covariation.driver_leads_h.eq(lag),'spearman_rho'].iloc[0]
    def o(loc,var,w,field='mean'):
        return obs.loc[obs.location.eq(loc)&obs.variable.eq(var)&obs.window_h.eq(w),field].iloc[0]
    def e(name,field):return evidence.loc[name,field]
    def p(period,clock,h):return profile.loc[profile.period.eq(period)&profile.clock.eq(clock)&profile.measure.eq('T')&profile.height_m.eq(h),'mean'].iloc[0]
    display=top[['selection_rank','factor','label','location','event_value','unit','percentile','median_q','settings_top5_frequency']].copy()
    display.columns=['排名','因素','代表特征','位置','事件前值','单位','历史百分位','校准尾部比例中位数','设置入选率']
    for c in ['事件前值','历史百分位','校准尾部比例中位数','设置入选率']:display[c]=display[c].map(lambda x:fmt(x,5 if c=='事件前值' else 3))
    display['位置']=display['位置'].map({'station':'本站','source':'源区ERA5'})
    compare=rank[['group','factor','label','event_value','percentile','median_q','valid_folds','selected_top5']].copy()
    compare.columns=['组','因素','代表特征','事件前值','历史百分位','校准尾部比例中位数','有效划分数','主前五']
    compare=compare.astype(object).fillna('不可评估')
    csv_dump(display,TABLES/'top5_chinese.csv')
    nominal=pd.read_csv(TABLES/'matched_anchors.csv',parse_dates=[0])
    avail=nominal.groupby(nominal.iloc[:,0].dt.year)[CATALOG.feature.tolist()].count().T
    avail.index.name='feature';csv_dump(avail,TABLES/'feature_year_availability.csv',True)
    manuscript_note='本章为单事件事后环境关联分析；未估计触发阈值、未来时间概率或动力学传播。'
    grid_limit=(f"主格点模式地形约{spatial['model_primary_elevation_m']:.0f}m，参考冰川掩膜内高程中位数约"
      f"{spatial['reference_glacier_median_elevation_m']:.0f}m，模式冰川比例约{spatial['model_primary_glacier_fraction']*100:.2f}%。"
      "格点明显混合较低地形和非冰川下垫面；本项目的源区ERA5实际指源区邻域环境背景，不能当作高位冰崖热状态或冰面通量。")
    report=f'''# 第一问完整计算结果

## 结果先读

主方案得到的前五项为：**土壤湿润变化、温度状态与变化、潜热交换、空气湿度、近地层热力分层**。代表指标及数值如下。G1与G5的中位校准尾部比例相同，名次2、3不表示可精确区分其强弱。

{display.to_markdown(index=False)}

**这些是相对前五，不是五个已经确认的直接致灾因子。** 五项的中位组校准尾部比例均高于0.05；完整筛选程序的{summary['pseudo_comparisons']}次相关伪事件比较中，约{summary['pseudo_exceedance']:.1%}的伪事件前五分数和不低于在同一校准集下的真实事件。不能认定本次环境组合在该历史基线下具有显著的整体特殊性，更不能据此证明灾害因果。

本文按指定的3.1—3.5结构完成全部计算与叙述。论文源文件见`manuscript/`，5组主要图及可编辑SVG见`results/figures/`，31列字典、全部数值和分折结果见`results/tables/`。

## 3.1 候选物理因素与特征量化方法

使用题给MET、RADM、SOIL、FLUX的24个CSV原始副本，重建63个测量变量的分析视图；新增ERA5-Land13变量、17个月、每变量12528个UTC小时，按清单读取14个核心NC。供方源QC为0的值进入主分析；FLUX无源QC，保留独立质量规则及敏感性结果。源区主格点为{spatial['primary_cell'][0]:.1f}°N、{spatial['primary_cell'][1]:.1f}°E，由参考冰川掩膜几何中心{spatial['reference_centroid']['latitude']:.4f}°N、{spatial['reference_centroid']['longitude']:.4f}°E确定，未按异常大小选点。

按照10个物理组、14类指标定义实现31列：本站18列、源区13列。均值要求至少90%有效且没有整段6h全空；完整累计与极值不容许缺小时。相邻24h均温差、四分量净辐射、2至20m温度梯度均由同时段数据计算。主截点为北京时间2026-08-26 10:00，事件参考为10:30。本站标签保守视为起点，原始09:00行对应10:00结束；标签为终点的解释已列为敏感性。

站点时间转UTC后与ERA5对齐；ARCO的降水与向下短长波已是小时增量，不二次反累计；原CDS的净短长波、感热和潜热按01UTC周期重置及00UTC前日总量规则反累计。相同格点坐标先规范小数精度，避免跨通道错误对齐。本站热通量供应符号未核实，源区按向上为正输出；两地通量不进行未经定义确认的方向归因。

文献用于界定可观测过程而非指定答案：Srivastava等的单事件气象分析启发了温度、风、辐射和湍流过程；Zhong等的源区/轨迹划分提醒不能将不同空间对象的量直接替换。没有将文献模型重要性或触发数值移植为本题结论。

## 3.2 大气边界层结构特征分析

灾前7天观测站呈明显昼夜差异。按原始北京时间11—17时和00—06时分组，最后3天的2m白天气温为{p('late_3d','day',2):.2f}℃，20m为{p('late_3d','day',20):.2f}℃；夜间分别为{p('late_3d','night',2):.2f}℃和{p('late_3d','night',20):.2f}℃。前7至3天的2m白天均温为{p('early_4d','day',2):.2f}℃，后3天更暖。昼夜分组为固定钟点描述，不宣称精确日出日落分类。

最后6h的平均温度梯度为{e('station__GTmean6','event_value'):.5f}℃/m，历史同期约第{e('station__GTmean6','percentile'):.2f}百分位；最后24h平均梯度为{o('station','GT',24):.5f}℃/m。多数时段气温随高度降低，短时可转为弱正梯度。该量仅表征1—20m近地层分层，不足以严格判定完整边界层高度或源区层结。

最后6h TKE为{e('station__TKEmean6','event_value'):.4f}m²/s²、摩擦速度为{e('station__USTARmean6','event_value'):.4f}m/s，相对可用历史样本分别处在{e('station__TKEmean6','percentile'):.2f}与{e('station__USTARmean6','percentile'):.2f}百分位，未显示该截点的极端湍流增强。2022年匹配窗口的FLUX候选全部不可用，因而G10不能通过本方案共同年份要求；缺乏组排名不表示湍流没有作用。

![近地层结构](../results/figures/fig3_1_boundary_layer.png)

图3-1：本站多高度温湿风廓线与灾前GT/TKE。虚线与实线区分前7至3天和最后3天；昼夜分别按固定北京时间窗口。时间轴为北京时间，竖线为题设参考时刻。数据来源为`boundary_layer_profiles.csv`与`station_process.csv.gz`。

## 3.3 灾前天气过程与地气水热响应

本站最后24h均温为{o('station','T2',24):.3f}℃，最后72h为{o('station','T2',72):.3f}℃，且日变化明显。相邻24h均温差为{e('station__dT24','event_value'):.3f}℃；源区ERA5对应变化为{e('source__dT24','event_value'):.3f}℃，表明临近截点的短时温变不完全同向，不能将站点回暖无条件外推至源区。两地24h均温在各自历史中的位置均偏高，但源区约第{e('source__Tmean24','percentile'):.2f}百分位，弱于本站。

本站72h累计净辐射约{e('station__RnEnergy72','event_value'):.2f}MJ/m²，源区约{e('source__RnEnergy72','event_value'):.2f}MJ/m²。两地都呈日周期与天气调制；它们是不同下垫面和尺度的地表能量交换背景，不能当作实际冰崖融化能量。源区24h向上潜热交换为{e('source__LEmean24','event_value'):.2f}W/m²，正值表示本项目转换约定下的向上交换，不能解读成同量的冰体融水。

![热状态与能量过程](../results/figures/fig3_2_energy_process.png)

图3-2：灾前30天热状态与地气交换，绘图采用6h滚动均值以便阅读，统计和排序仍严格采用字典中的窗口。本站保留供应通量符号，ERA5向上为正，不能仅凭曲线同号作热流方向验证。

本站前24h与72h降水均为{o('station','P',24,'sum_complete'):.1f}mm，前168h为{o('station','P',168,'sum_complete'):.1f}mm；源区ERA5分别为{o('source','P',24,'sum_complete'):.2f}、{o('source','P',72,'sum_complete'):.2f}、{o('source','P',168,'sum_complete'):.2f}mm。两地明显不同，本站无雨不能代表源区无水源。源区这三项累计量在历史参照中约为第{e('source__Rain24','percentile'):.1f}、{e('source__Rain72','percentile'):.1f}和{e('source__Rain168','percentile'):.1f}百分位，当前格点不支持灾前累计降水异常偏高；格点结果也不能排除局地微尺度强降水。

本站0.1m含水量在灾前7天整体下降，最后24h平均为{o('station','VWC01',24):.5f}m³/m³，端点变化为{e('station__dVWC24','event_value'):.5f}m³/m³。深层变化更缓，浅层土温日振幅较大，体现本地陆面水热响应；未观测到源区基底水压，不能把本站变干解释成冰体失稳的直接水力机制。

![水分过程与土壤响应](../results/figures/fig3_3_water_process.png)

## 3.4 极端气象条件与历史异常识别

主参照取2021—2025年8月11日至9月10日相同钟点，共155个名义锚点，逐列保留实际有效数，各年份等权。31列均计算历史分位与经验尾部比例，降水/风速按事先声明考察上尾，其余采用双侧。对同一变量的多个窗口及位置采用一致口径，未把背景日期标为确认无灾样本。

本站24h均温约第{e('station__Tmean24','percentile'):.2f}百分位，前24h浅层含水量变化约第{e('station__dVWC24','percentile'):.2f}百分位，分别表示偏暖和较明显的本地干燥变化。在末7天逐小时滚动特征中，本站均温超出同期5%—95%带共{int(duration.loc['station__Tmean24','outside_hours'])}h；含水量变化超带共{int(duration.loc['station__dVWC24','outside_hours'])}h，最长连续{int(duration.loc['station__dVWC24','longest_outside_h'])}h。这是相关滚动窗口的持续性描述，不是多次独立极端事件。

源区潜热交换约第{e('source__LEmean24','percentile'):.2f}百分位、相对湿度约第{e('source__RHmean24','percentile'):.2f}百分位，均未超出事件截点的历史5%—95%区间。本站最大小时风速为{e('station__Umax24','event_value'):.3f}m/s，历史约第{e('station__Umax24','percentile'):.2f}百分位；不宜称灾前极端强风。土壤和通量的异常也不全部等同“极端天气事件”。

![历史同期异常](../results/figures/fig3_4_historical_anomalies.png)

图3-4：阴影是2021—2025年同季节同小时的经验5%—95%带，不是置信区间或预测区间。均温与土壤变化存在局部越界，源区潜热与湿度在历史正常波动范围内；未为配合题目措辞而强行宣布所有因素极端。

## 3.5 灾害关联证据评价与五因素筛选

对五历史年作十种“3年参照＋2年校准”划分。每组对固定可用的候选版本取最大异常，校准历史也执行相同选择。再按有效划分中位校准尾部比例排序，每组最多一项，并检查预先规定的温度/分层及风/湍流耦合对。跨组特征相关仅用于识别冗余，未充当与灾害的相关系数。

### 十组完整比较

{compare.to_markdown(index=False)}

G10历史支持不足是因为2022年匹配FLUX数据缺失；它仍完成了时序、廓线相关分析与可用样本的单列异常评价。剔除2022年的四年敏感性中可评价，但不能倒过来把四年版冒充预先要求的五年主方案。

### 前五因素的解释

1. **土壤湿润变化（G8）**：代表为本站24h浅层含水量端点变化，表现为偏干。统计上相对罕见并持续，但直接测量对象是本站土壤，不是上游冰体或沟床孔压。因此它是区域陆面响应线索，不能称本次冰崩的首要直接原因。
2. **温度状态与变化（G1）**：代表为本站24h均温。本站偏暖且源区均温也偏向自身历史上部，但源区短时温变不完全同步。可作为区域热背景，不能直接推出融化量和失稳时间。
3. **潜热交换（G5）**：代表为源区格点24h均值。当前值处于历史较高但非极端位置；它入选五因素是相对于其他候选的结果，不等于物理贡献排名第三。再分析下垫面和本站符号限制需保留。
4. **空气湿度（G7）**：代表为源区24h相对湿度，较自身背景偏低。本站也相对偏干，但绝对湿度因位置不同而不同；不能用RH下降单独证明水量供应不足或冰体破坏。
5. **近地层热力分层（G9）**：代表为本站6h平均温度梯度。其历史位置并不极端；22种同候选范围设置中约{sens.loc['G9','selection_frequency_all']:.1%}入选，弱于前四项的稳定性，部分情景由辐射或感热组替代，应列为较弱的第五候选。

22种同范围设置中，G8/G1/G5/G7均入选；另有2种缩小候选位置的对照不混入此分母。十种年份划分彼此共享资料，设置入选率也不是置信水平或致灾概率。全部设置、被替代组、历史样本数、候选可用性和去冗余记录均随代码交付。

完整伪事件诊断中，真实事件的前五组合并没有持续优于历史伪事件：相关比较的超过比例为{summary['pseudo_exceedance']:.1%}。故本题在现有单事件资料下可以给出上述可复现的相对候选排序，但不能宣称识别了五个已证实的触发原因。尤其本站远离源区、ERA5不能解析冰崖微尺度、气象记录不含地质力学状态，这些是本结论的具体适用边界。

![组排序与稳健性](../results/figures/fig3_5_ranking_stability.png)

![伪事件全流程诊断](../results/figures/supp_pseudo_event_diagnostic.png)

## 复现与完整性

1. 在本文件夹创建Python环境并安装`requirements.txt`，执行`python run.py`即可从复制的原始数据重建全部分析、图表、报告和LaTeX源；有XeLaTeX时同时编译PDF。
2. `python -m unittest discover -s tests -v`检查日重置、跨缺月、缺值传播、窗口完整性、零值、经验比例与候选全集；`python scripts/verify_outputs.py`核查交付和输入哈希。
3. 程序运行不下载数据、不读外部工作区、不访问密钥。原始副本通过相对路径哈希清单追溯。虚拟环境不是研究数据，便携压缩包不包含它。
4. 输出目录：`results/tables/`完整数值；`results/figures/`PNG/PDF/SVG；`manuscript/`五节正文与独立PDF；`reports/`口径与验证；`data/raw/`原始副本；`data/input/`派生输入；`scripts/`实现。

## 来源与说明

- 原题、24个观测CSV、13项ERA5资料和两篇参考论文原文均在项目中保存，模型格点参考不等于实测释放区。
- 本站数据DOI：10.11888/Atmos.tpdc.303600。
- ECMWF ERA5-Land及ARCO累计规则见`docs/official_sources.json`；热通量方向另核对[ECMWF参数146](https://codes.ecmwf.int/grib/param-db/146)。
- Srivastava等（2022），DOI 10.3390/atmos13020267；Zhong等（2025），DOI 10.1007/s10346-024-02421-7。文献支持候选动机，不替代本次数值筛选。
- {manuscript_note}
'''
    mapping=pd.DataFrame([dict(因素组=g+' '+GROUPS[g],指标=GROUP_INDICATORS[g],
      指标家族=','.join(CATALOG.loc[CATALOG.group.eq(g),'indicator'].drop_duplicates()),
      列数=len(CATALOG[CATALOG.group.eq(g)]),研究视角=GROUP_VIEWS[g]) for g in GROUPS])
    methods=r'''统一算子为 $\overline X_w(t)=n_w^{-1}\sum_{k\in\mathcal V_w}X(t-k)$、$C_w(t)=\sum_{k=0}^{w-1}x(t-k)$、$\Delta T_{24}=\overline T_{24}(t)-\overline T_{24}(t-24)$。独立组合量为 $R_n=R_{sd}-R_{su}+R_{ld}-R_{lu}$、$E_{R,w}=0.0036\sum R_n$（MJ/m²）、$G_T=(T_{20m}-T_{2m})/18m$。浅层含水变化为 $VWC(t)-VWC(t-24h)$；风切变先将风速风向转为水平矢量，再取 $\sqrt{(u_{20}-u_2)^2+(v_{20}-v_2)^2}/18m$。完整31列逐项定义见 `results/tables/feature_catalog.csv`。

'''
    report=report.replace('按照10个物理组、14类指标定义实现31列：',grid_limit+'\n\n'+mapping.to_markdown(index=False)+'\n\n'+methods+'按照10个物理组、14类指标定义实现31列：')
    coupling=(f"矢量风切变最后6h均值为{b('vector_shear',6):.4f}s⁻¹，低于最后24h的{b('vector_shear',24):.4f}s⁻¹；TKE最后6h均值也低于最后24h的{b('TKE',24):.3f}m²/s²，说明临近截点交换较弱。"
      f"灾前7天逐小时TKE与风切变、摩擦速度的同步Spearman系数为{rho('vector_shear'):.3f}、{rho('USTAR'):.3f}；与感热/潜热为{rho('H'):.3f}/{rho('LE'):.3f}，对应通量领先3h时为{rho('H',3):.3f}/{rho('LE',3):.3f}。"
      "这些是同一周内含日周期的相关时序描述，不能识别因果时滞，也不参与灾害因素排序；0/3/6h全表见boundary_layer_covariation.csv。")
    report=report.replace('![近地层结构]',coupling+'\n\n![近地层结构]')
    report=report.replace('灾前GT/TKE','灾前GT/矢量风切变/TKE')
    (ROOT/'reports/第一问完整结果.md').write_text(report,encoding='utf-8')
    # Compact, manuscript-ready Chinese chapter; all numbers are emitted from tables.
    gtable=[]
    for g in GROUPS:
        classes=','.join(CATALOG.loc[CATALOG.group.eq(g),'indicator'].drop_duplicates())
        gtable.append(f'{g} {GROUPS[g]} & {GROUP_INDICATORS[g]}（{classes}） & {len(CATALOG[CATALOG.group.eq(g)])} & {GROUP_VIEWS[g]} '+r'\\')
    rtable=[]
    for r in rank.itertuples():
        rep='—' if pd.isna(r.representative) else ('站' if r.location=='station' else '源')+' '+r.label
        rtable.append(f'{r.group} & {r.factor} & {rep} & {fmt(r.event_value,3)} & {fmt(r.percentile,1)} & {fmt(r.median_q,3)} & {r.valid_folds}/10 '+r'\\')
    ttable=[]
    explanations={'G8':'本站干燥响应；非冰下水压','G1':'区域偏暖；非融化量','G5':'模式地气交换；非实测融水','G7':'自身背景偏干；非因果','G9':'近地层代理；第5名较敏感'}
    for r in top.itertuples():
        unit={'m3/m3':r'm$^3$/m$^3$','degC':r'$^\circ$C','W/m2':r'W/m$^2$','%':r'\%','degC/m':r'$^\circ$C/m'}[r.unit]
        ttable.append(f'{int(r.selection_rank)} & {r.factor} & {fmt(r.event_value,5 if r.group in ["G8","G9"] else 2)} {unit} & {r.settings_top5_frequency*100:.1f}\\% & {explanations[r.group]} '+r'\\')
    body=r'''\section{灾前大气环境特征与泥石流关联因素分析}
\subsection{候选物理因素与特征量化方法}
围绕题设“冰崩—碎屑流—泥石流—山洪”灾害链，以MET、RADM、SOIL、FLUX四类塔站小时观测为主体，结合源区邻域ERA5-Land资料，分析近地层结构、天气过程和极端性。参考单事件气象过程与源区/轨迹分离研究\cite{Srivastava2022,Zhong2025}，预先定义10个因素组、14类指标、31列特征（本站18列、源区13列），而非按数据文件分节或直接指定五个因素。完整31列公式、单位、窗口、质量规则随代码字典交付。

\begin{table}[!ht]\centering\small
\caption{预先定义的因素组与指标家族；同组不同位置、窗口共同校准。}
\begin{tabularx}{\linewidth}{lXrl}\toprule 因素组 & 指标定义及家族 & 列数 & 研究视角\\\midrule
'''+'\n'.join(gtable)+r'''
\bottomrule\end{tabularx}\end{table}

令$t$为已结束的小时端点，统一采用均值$\overline X_w$、小时增量累计$C_w$和相邻24h均温差：
\begin{equation}
\overline X_w(t)=\frac{1}{n_w}\sum_{k\in\mathcal V_w}X(t-k),\quad C_w(t)=\sum_{k=0}^{w-1}x(t-k),\quad
\Delta T_{24}=\overline T_{24}(t)-\overline T_{24}(t-24).
\end{equation}
其中均值至少90\%有效，且无全空6h子段；累计与最大值要求完整。净辐射、累计能量及温度分层代理为
\begin{equation}
R_n=R_{sd}-R_{su}+R_{ld}-R_{lu},\quad E_{R,w}=0.0036\sum R_n\;(\mathrm{MJ/m^2}),\quad
G_T=\frac{T_{20m}-T_{2m}}{18m}.
\end{equation}
各分量先同期配对。$E_R$基于小时平均通量近似，不能解释为冰面实际融化能；$G_T$也不是完整边界层高度。

本站按UTC+8统一时区，主分析保守使用原始09:00及以前小时，最后完整端点为8月26日10:00，题设参考为10:30；小时标签为终点及截点提前1/3h另作敏感性。ARCO降水/向下辐射已为小时增量，原CDS净辐射/热通量按每日周期反累计\cite{ERA5}。主分析有源QC者仅用0；缺测不填0、不插值。ERA5主点由参考冰川掩膜几何中心确定为28.3$^\circ$N、85.5$^\circ$E，不按2026异常选点。本站远离源区且不在下载矩形内，故两地不是同址验证。

\subsection{大气边界层结构特征分析}
''' + f'''灾前7天近地层呈明显昼夜差异。固定北京时间11—17时为昼、00—06时为夜，最后3天2m/20m昼均温为{p('late_3d','day',2):.2f}/{p('late_3d','day',20):.2f}$^\\circ$C，夜均温为{p('late_3d','night',2):.2f}/{p('late_3d','night',20):.2f}$^\\circ$C；前7至3天的2m昼均温为{p('early_4d','day',2):.2f}$^\\circ$C。白天风随高度增强、湿度低于夜间，近地层温度梯度多数为负并有短时反转，说明存在随日周期变化的分层与交换过程。\n\n''' + r'''
\begin{figure}[!ht]\centering\includegraphics[width=\linewidth]{../results/figures/fig3_1_boundary_layer.pdf}
\caption{多高度温湿风廓线与灾前分层、湍动能。廓线虚/实线为前7至3天/最后3天；昼夜按固定钟点。时间轴为北京时间，竖线为题设参考，曲线不含灾后值。}\end{figure}
''' + f'''最后6h的$G_T$为{e('station__GTmean6','event_value'):.5f}$^\\circ$C/m，TKE为{e('station__TKEmean6','event_value'):.4f}m$^2$/s$^2$，$u_*$为{e('station__USTARmean6','event_value'):.4f}m/s，相对可用历史样本分别处在第{e('station__GTmean6','percentile'):.1f}、{e('station__TKEmean6','percentile'):.1f}、{e('station__USTARmean6','percentile'):.1f}百分位，未显示该截点的极端湍流增强。2022年匹配FLUX缺测导致湍流组不能进入严格的五年组校准，但不影响本节对有效观测过程的描述。20m塔只能反映本站近地层，不能代表源区冰崖或完整边界层。\n\n''' + r'''
\subsection{灾前天气过程与地气水热响应}
''' + f'''本站最后24h均温为{o('station','T2',24):.2f}$^\\circ$C，72h均温为{o('station','T2',72):.2f}$^\\circ$C，日变化明显且末期总体偏暖。相邻24h温差本站为{e('station__dT24','event_value'):.3f}$^\\circ$C，源区为{e('source__dT24','event_value'):.3f}$^\\circ$C，短时温变并非完全同步。两地72h净辐射能分别为{e('station__RnEnergy72','event_value'):.2f}和{e('source__RnEnergy72','event_value'):.2f}MJ/m$^2$；源区24h潜热交换为{e('source__LEmean24','event_value'):.2f}W/m$^2$。这些量描述热背景及地气交换，不能直接换算为冰体融化或失稳贡献。\n\n''' + r'''
\begin{figure}[!ht]\centering\includegraphics[width=\linewidth]{../results/figures/fig3_2_energy_process.pdf}
\caption{灾前30天热状态与能量过程，作图为6h均值。本站保留供应通量符号，ERA5转换为向上正；未核实本站符号前，两地通量不作同向归因。}\end{figure}
''' + f'''本站前24/72h降水均为0，168h为{o('station','P',168,'sum_complete'):.1f}mm；源区ERA5分别为{o('source','P',24,'sum_complete'):.2f}、{o('source','P',72,'sum_complete'):.2f}、{o('source','P',168,'sum_complete'):.2f}mm。本站无雨不等于源区无水源。源区这三项处在历史第{e('source__Rain24','percentile'):.1f}、{e('source__Rain72','percentile'):.1f}、{e('source__Rain168','percentile'):.1f}百分位，本格点未见累计降水异常偏高，但不能排除未解析的局地天气。本站0.1m土壤湿度在一周内下降，末24h均值为{o('station','VWC01',24):.5f}m$^3$/m$^3$、24h变化为{e('station__dVWC24','event_value'):.5f}m$^3$/m$^3$；深层变化更缓。这是本地陆面响应，不能替代冰川基底水压。\n\n''' + r'''
\begin{figure}[!ht]\centering\includegraphics[width=\linewidth]{../results/figures/fig3_3_water_process.pdf}
\caption{最后7天水分过程与本站土壤响应。源区与本站降水不同；土壤湿度、土温的深度差异不能外推成源区直接测量。}\end{figure}

\subsection{极端气象条件与历史异常识别}
在2021—2025年各取8月11日至9月10日同钟点，得到155个名义历史锚点；按实际有效数记录、年份等权。降水和风速采用预先规定的上尾，其余采用双侧经验尾部比例$r_j$，异常分数为$A_j=-\log_{10}r_j$。保留并列值与零值，经验比例不称独立样本p值。逐小时历史带匹配同季节同钟点，滚动窗口的超带时长只是持续性描述。
''' + f'''本站24h均温为第{e('station__Tmean24','percentile'):.2f}百分位，浅层含水量24h变化为第{e('station__dVWC24','percentile'):.2f}百分位，分别偏暖与偏干。最后7天两者超出历史5\\%—95\\%带分别为{int(duration.loc['station__Tmean24','outside_hours'])}h和{int(duration.loc['station__dVWC24','outside_hours'])}h；土壤变化最长连续超带{int(duration.loc['station__dVWC24','longest_outside_h'])}h。源区潜热和湿度为第{e('source__LEmean24','percentile'):.2f}、{e('source__RHmean24','percentile'):.2f}百分位，事件截点未超该区间；本站24h最大小时风速{e('station__Umax24','event_value'):.3f}m/s也仅约第{e('station__Umax24','percentile'):.1f}百分位。不能把全部环境异常混称极端天气，更不能预设暴雨或强风结论。\n\n''' + r'''
\begin{figure}[!ht]\centering\includegraphics[width=\linewidth]{../results/figures/fig3_4_historical_anomalies.pdf}
\caption{代表特征与历史同期中位数、5\%—95\%经验带。阴影不是预测/置信区间。可见本站干燥变化持续，源区潜热和湿度仍在历史波动范围内。}\end{figure}

\subsection{灾害关联证据评价与五因素筛选}
五个历史年按3年参照、2年校准作10种划分。每组取固定可用候选的最大异常$M_g=\max_j A_j$；历史校准也执行同样挑选，以校准尾部比例$Q_g$消除不同候选数的机会差异。每折真实与历史使用同一列全集。参照/校准每年至少15个有效锚点，不足则不可评估。各组中位$Q_g$越小，相对证据越强；至少60\%划分有效才能参加主前五。每组最多一个代表，跨组相关只作预先规定耦合组的冗余检查，不充当致灾关联。

\begin{table}[!ht]\centering\scriptsize
\caption{十组完整比较。历史百分位对应代表列，$Q$对应组内多版本校准后的中位比例；二者不等同。}
\begin{tabularx}{\linewidth}{llXrrrr}\toprule 组 & 因素 & 代表指标（站/源） & 事件前值 & 百分位 & $Q$ & 有效折\\\midrule
'''+'\n'.join(rtable)+r'''
\bottomrule\end{tabularx}\end{table}

\begin{table}[!ht]\centering\scriptsize
\caption{最终五因素及证据边界。入选率的分母为22种同候选范围设置，不是独立灾害次数。}
\begin{tabularx}{\linewidth}{rlrlX}\toprule 排名 & 因素 & 代表值 & 设置入选率 & 解释边界\\\midrule
'''+'\n'.join(ttable)+r'''
\bottomrule\end{tabularx}\end{table}

''' + f'''相对前五为土壤湿润变化、温度状态与变化、潜热交换、空气湿度和近地层分层。G1/G5中位$Q$同为{top.loc[top.group.eq('G1'),'median_q'].iloc[0]:.3f}，2/3次序只作展示，不宣称二者可精确区分。前四项在22种同范围设置均入选，第五项约{sens.loc['G9','selection_frequency_all']*100:.1f}\\%，部分设置由辐射或感热替代，故第五候选较弱。湍流无主排名源于2022年缺测；剔除该年的可用性结果仅作补充，不据此认定湍流无影响。\n\n''' + r'''
\begin{figure}[!ht]\centering\includegraphics[width=\linewidth]{../results/figures/fig3_5_ranking_stability.pdf}
\caption{组校准异常与设置稳健性。色阶为名次，灰白空格为不可评价；完整设置对应CSV。排名稳定不等于该因素具有因果贡献。}\end{figure}
''' + f'''进一步将历史校准期按7天留块并排除与168h窗口重叠部分，真实和伪事件在同一剩余校准集执行全套组筛选。{summary['pseudo_comparisons']}次相关比较中，有{summary['pseudo_exceedance']*100:.1f}\\%的伪事件前五分数和不低于真实事件；同时五项中位$Q$均高于0.05。因此整体特殊性证据有限，不将五项升级为已证实的直接触发原因。本站土壤偏干只能解释当地陆面响应；区域偏暖不能直接推出源区融化，源区通量与湿度仅为格点环境背景。上述单事件相对排名可为后续研究提出候选，但不提供普适灾害发生概率。\n\n''' + r'''
\begin{thebibliography}{9}\small
\bibitem{Srivastava2022} Srivastava P, Namdev P, Singh P K. 7 February Chamoli Rock-Ice Avalanche Disaster: Model-Simulated Prevailing Meteorological Conditions. Atmosphere, 2022, 13:267. doi:10.3390/atmos13020267.
\bibitem{Zhong2025} Zhong Y, et al. Unravelling driving conditions of rock and ice avalanches and resulting cascading processes in High Mountain Asia. Landslides, 2025, 22:989--1001. doi:10.1007/s10346-024-02421-7.
\bibitem{ERA5} ECMWF. ERA5-Land data documentation and ARCO Product User Guide. Copernicus Knowledge Base. 累计规则与参数方向说明；数据源地址随项目附录交付。
\end{thebibliography}
'''
    # Keep the dedicated LaTeX project independently compilable in its viewer.
    (ROOT/'manuscript/figures').mkdir(exist_ok=True)
    for figure in (ROOT/'results/figures').glob('fig3_*.pdf'):
        shutil.copyfile(figure,ROOT/'manuscript/figures'/figure.name)
    body=body.replace('../results/figures/','figures/')
    compact_coupling=(f"最后6h矢量风切变为{b('vector_shear',6):.4f}s$^{{-1}}$，低于24h的{b('vector_shear',24):.4f}s$^{{-1}}$；"
      f"TKE也低于24h的{b('TKE',24):.3f}m$^2$/s$^2$。一周内TKE与风切变、$u_*$同步Spearman系数为{rho('vector_shear'):.2f}/{rho('USTAR'):.2f}，"
      f"与H/LE为{rho('H'):.2f}/{rho('LE'):.2f}；含共同日周期，仅描述协变，不作因果或排名依据。")
    body=body.replace('20m塔只能反映本站近地层，不能代表源区冰崖或完整边界层。',compact_coupling+'20m塔只能反映本站近地层，不能代表源区冰崖或完整边界层。')
    body=body.replace('灾前分层、湍动能','灾前分层、矢量风切变及湍动能')
    body=body.replace('[!ht]','[H]')
    body=body.replace('本站远离源区且不在下载矩形内，故两地不是同址验证。',
      '本站远离源区且不在下载矩形内，故两地不是同址验证。'+
      f"主格点模式高程约{spatial['model_primary_elevation_m']:.0f}m，参考冰川高程中位数约{spatial['reference_glacier_median_elevation_m']:.0f}m，冰川比例约{spatial['model_primary_glacier_fraction']*100:.1f}\\%；因此格点热湿量只能解释区域背景，不能视为真实冰面通量。")
    (ROOT/'manuscript/q1_section.tex').write_text(body,encoding='utf-8')
    notes='''# 写作与证据核查

本章按提供的五节结构组织；数值均由结果CSV读取生成，不手填预期的前五。

| 主张 | 数据证据 | 状态 |
|---|---|---|
| 本站末期偏暖、浅层土壤持续变干 | process_observations、historical_envelopes、anomaly_durations | 支持当地描述 |
| 本站无雨不代表源区无雨 | 两地累计降水及各自历史分位 | 支持空间差异，非微尺度实测 |
| 五因素相对排序可复算 | group_rankings、fold_rankings、sensitivity_rankings | 支持限定候选集内排名 |
| 本次组合整体特别罕见 | 留块全流程伪事件 | 不支持强主张 |
| 已证明五项直接触发灾害 | 没有岩体/冰体内部力学与多事件证据 | 不支持 |

术语：特征为31列计算量，因素组为G1至G10；历史带为经验分位带，校准尾部比例不是因果概率；触发时间、口岸到达与题设参考时刻不混用。

仍存在的实质限制：本站小时起止标签和通量符号未完全核实（端点与QC已做敏感性）；ERA5格点不能解析冰崖；本站与源区非同址；2022年FLUX缺测限制G10校准。没有把这些限制靠插值、填零或虚构事件标签消除。
'''
    (ROOT/'reports/写作与证据核查.md').write_text(notes,encoding='utf-8')
    print('Generated Chinese numerical report and five-section LaTeX chapter.',flush=True)

if __name__=='__main__':main()
