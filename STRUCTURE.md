# 论文结构与编辑位置

本结构按用户于2026年10月26日提供的提纲建立。入口仍为 `main.tex`，每章一个文件，共8章、36个二级标题；参考文献之后为附录。

| 内容 | 编辑文件 | 二级标题数 |
| --- | --- | --- |
| 摘要、关键词、题目及赛事信息 | `main.tex` | — |
| 1 引言与问题分析 | `sections/01-introduction.tex` | 3 |
| 2 研究区域、数据体系与预处理 | `sections/02-data.tex` | 5 |
| 3 灾害前环境异常与关键关联因素识别（问题一） | `sections/03-factors.tex` | 5 |
| 4 泥石流触发临界条件与风险评估（问题二） | `sections/04-thresholds.tex` | 6 |
| 5 触发时间预测与时空预警（问题三） | `sections/05-warning.tex` | 6 |
| 6 泥石流灾害链的动力过程模拟（问题四） | `sections/06-simulation.tex` | 6 |
| 7 模型综合评价与防灾策略 | `sections/07-evaluation.tex` | 3 |
| 8 结论 | `sections/08-conclusion.tex` | 2 |
| 参考文献 | `references.bib`；输出位置在 `main.tex` | — |
| 附录A 数据与预处理补充说明 | `sections/09-appendix.tex` | — |
| 附录B 使用的软件与运行命令 | `sections/09-appendix.tex` | — |
| 附录C 计算机源程序 | `sections/09-appendix.tex`、`code/` | — |

## 填写方法

每个二级标题下的 `%` 注释保留了用户给出的写作要求。请在其下填写正文，并删除该处的 `\writingplaceholder`。同一命令留在尚未填写的小节中即可，它只产生空白段落，以便空提纲正常分页。

所有文件已有独立的交叉引用标签，`sections/` 中均设置 `% !TeX root = ../main.tex`。编辑后保存，LaTeX Workshop会构建主文件，输出至 `build/main.pdf`。

第一页面保留题目、摘要、关键词和赛事信息；第二页面保留单页目录。由于二级标题较多，目录仅显示一级标题及参考文献、附录，正文仍按1.1至8.2完整编号。章节号由LaTeX自动生成，不手写数字。

第一问已填入完整五节结果、5组图和3张表，实际引用已并入文献库。其余章节仍按现有状态保留；1.3技术路线图和附录整合待后续完成。第一问复算工程位于 `code/question1/`。旧版演示已归档到 `examples/previous-template/`，不会混入正文。

## 第一问编辑入口

正文：`sections/03-factors.tex`；三张表：`tables/question1/`；全部主图和补充诊断：`figures/question1/`。图表均有标签，可用 `\ref` 交叉引用。完整数据、脚本和结果保存在 `code/question1/`；复算输出到该工程自身目录，正式论文内容按需人工更新。详见 `writing/第一问移植说明.md`。
