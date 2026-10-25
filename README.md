# MathorCup 2026 融合模板

入口为 `main.tex`。本项目独立保存在 `C:\Users\21800\Desktop\mathor\MathorCup2026`，与原 `latex` 文件夹并列。本模板按本届大数据竞赛要求设置首页、目录与页码，正文参考 ElegantPaper 的字体搭配、1.35 倍行距、标题与图表样式。

本目录是正式主工作项目，不接收 GitHub 模板的自动覆盖。GitHub 下载、更新与对照统一在 `C:\Users\21800\Desktop\mathor\latex\github` 完成；需要融合的部分由用户决定后逐项修改。详见本目录 `AGENTS.md`。

本目录有独立的本地 Git 仓库，用于记录论文修改历史；目前没有远程仓库，不参与 GitHub 同步。它与 `../latex/.git` 的历史和远程配置相互独立。VS Code 请分别用两个窗口打开两个项目根目录，不要把父目录 `mathor` 作为统一工作区。主项目首次保存版本时，先检查源代码管理中的文件，再暂存并提交。

## 开始使用

建议在 VS Code 中打开本目录，编辑 `main.tex` 的队伍编号、赛道、题目和关键词，然后修改 `sections/` 内的正文。保存后由 LaTeX Workshop 自动编译。正文子文件均已设置 TeX root，可在编辑章节时自动构建主文件。

在本目录的终端运行：

```powershell
latexmk -xelatex -outdir=build main.tex
```

在父工作文件夹的终端运行：

```powershell
latexmk -cd -xelatex -outdir=build MathorCup2026/main.tex
```

输出为 `build/main.pdf`。Biber、交叉引用与重复编译由 latexmk 自动完成，无需手动调用 BibTeX。

## 页面要求

- 第一物理页：队伍编号、赛道、题目、摘要和关键词；不显示页码。
- 第二物理页：目录；不显示页码。默认收录一级、二级标题。
- 第三物理页起：正文，页脚中央只显示阿拉伯数字，从 1 连续编号；全文无页眉。
- 摘要或目录超过一页时，模板报错提示，避免打乱规定的页面顺序。目录过长可在导言区设置 `\setcounter{tocdepth}{1}`。
- 不填写姓名、学校、指导教师等身份信息；不添加作者、单位、日期或版本栏。
- 正文控制在 30 页以内；附录另起一页，继续页码，页数不限。模板对附录前超过 30 页给出提示，最终仍应人工检查。
- 承诺书单独签名和提交，不拼入匿名论文。
- 最终上传前，按所选赛道和正式队号重命名 PDF，例如规范中的 `A2600001.pdf`。

## 文件结构

```text
MathorCup2026/
  main.tex                   入口、赛事信息和摘要
  mathorcup-elegant.cls       页面结构与正文排版
  mathorcup2026.bbx           参考文献列表样式
  mathorcup2026.cbx           正文引用样式
  references.bib             文献库
  sections/                  正文及附录
  figures/                   示例图片
  code/                      附录源程序
  fonts/                     本地字体
  licenses/                  字体许可证与来源说明
  requirements/              本届格式要求原文件副本
  .vscode/settings.json      工作区编译配置
  latexmkrc                  自动编译配置
  DEPENDENCIES.md             依赖清单与验证说明
  build/                     编译产物，Git 忽略
```

正文用 `\cite{键}` 引用文献；书籍用 `\cite[第23--25页]{键}` 指出引用页码。文献按首次引用顺序生成。图、表、公式用 `\label`、`\ref`、`\eqref` 自动编号。

本目录包含所有模板专用文件及字体，没有对下载目录、父级模板或网络图片的运行时依赖。通用宏包和 XeLaTeX、Biber、latexmk 由完整安装的 TeX Live 提供，不复制整个发行版。

示例正文、数据和文献均为占位演示，提交前必须替换。

## 格式依据与来源

优先依据 `requirements/` 中本届《论文格式及提交规范》和同届 Word 论文模板。旧 MathorCup 模板的“第 X 页 共 Y 页”页脚、题号字段等已按本届要求调整。

正文风格参考 ElegantLaTeX/ElegantPaper 0.12；赛事字段接口参考本机 MathorcupLatexTemplate 的 `bianhao`、`tihao`、`timu`、`keyword`。融合类独立实现，避免同时加载两套文档类产生冲突。
