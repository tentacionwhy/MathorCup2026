# MathorCup赛道B：第一问完整复现项目

本文件夹独立保存完成第一问所用的代码、原始数据副本、派生表、图、结果说明与论文LaTeX。范围仅第一问，不包含第二至四问。无需访问原先桌面数据目录，无需联网下载，不包含API密钥。

## 先看结果

- `reports/第一问完整结果.md`：数值、五节解释和全部图表。
- `manuscript/main.pdf`：可独立阅读的第一问正文；`q1_section.tex`为可接入整篇论文的章节源。
- `results/tables/top5_evidence.csv`：主前五及统计、持续性、稳健性和解释限制。
- `results/tables/group_rankings.csv`：十组完整比较，历史支持不足的组不伪造排名。
- `reports/analysis_protocol.md`：时间、QC、累计量、历史对照和筛选规则。
- `reports/交付与验收.md`：按方案逐项验收、文件入口与验证结果。

重要结果：前五是单事件相对候选排序；完整伪事件检验未支持本次环境组合特别罕见。不得将其当作五个已证实的直接致灾原因。第五项对设置较敏感，湍流组受2022年缺测影响；详见报告。

## 一键运行

Python 3.11或更高版本，建议使用单独环境。在本目录运行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

如果只需要数值、图、报告和LaTeX源而不编译正文PDF：

```powershell
.\.venv\Scripts\python.exe run.py --skip-compile
```

PDF正文编译需要安装XeLaTeX与ctex（如TeX Live）。所有Python文件使用自身位置确定根目录及其相对路径，可从其他当前目录调用。虚拟环境不是研究数据；便携压缩包不含`.venv/`，复制/解压后按上述步骤重建环境。`requirements-lock.txt`记录本次实际环境版本。

## 数据与文件结构

```text
config/                 固定分析配置
data/raw/hourly/        MET RADM SOIL FLUX原始CSV，共24份
data/raw/era5_land/     14个核心NC及冰川几何参考
data/raw/problem/       原题PDF
data/raw/literature/    两篇方法背景论文
data/input/             本项目重建的QC视图、ERA5小时量、31列特征
metadata/               字典、下载清单、输入SHA256、空间提取与图源数据说明
scripts/                数据处理、特征、排名、稳健性、过程、作图与报告
tests/                  有效规则和边界情形测试
results/tables/         完整数值与CSV源数据
results/figures/        5组正文图PDF/SVG/PNG与补充伪事件诊断
manuscript/             main.tex、五节正文及编译PDF
reports/                完整结果、口径、证据核查与交付验证
docs/                   用户最终方案、已有实施规则和文献阅读依据
logs/                   每阶段日志
```

复算使用输入清单所列的原始资料和参考。五县日均温不参与本轮计算，因此不复制为必需输入；其他未用附件、全球ERA5静态原件和下载缓存不重复打包。所用局部模式静态表另存`data/input/model_grid_static_reference.nc`。本地文件夹中的源下载缓存不参与分析，也不进入便携压缩包。

## 各阶段

`prepare.py`从原始副本重建本站质量视图与ERA5小时单位。`features.py`完整计算31列。`ranking.py`执行十种年份划分、组内多版本校准、去冗余及留块伪事件。`sensitivity.py`运行季节宽度、年份、QC、覆盖、截点、时段标签、通量审查和格点对照。`process_analysis.py`生成廓线、时序、历史带与证据。`plot_results.py`导出5组正文图和补充诊断。`write_report.py`从CSV生成中文结果和LaTeX。

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe run.py --verify-only
```

`metadata/input_manifest.json`中的路径全部相对于本目录。原始输入哈希固定；如主动更换数据，需新建分析版本和清单，不应跳过哈希验证。程序不会修改原始数据。不要把派生表、敏感性视图、相邻格点或历史重叠窗口计为额外独立灾害样本。
