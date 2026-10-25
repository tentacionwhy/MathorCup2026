# 依赖清单

主文件、章节、图片、代码、文献样式和字体均使用相对路径，可整体复制到其他安装完整 TeX Live 的电脑，无需联网下载模板附件。

## 项目内专用依赖

- `mathorcup-elegant.cls`
- `mathorcup2026.bbx`、`mathorcup2026.cbx`
- `references.bib`
- `sections/*.tex`
- `figures/model-workflow.pdf`
- `code/example.py`
- `fonts/*.otf`：Fandol 中文字体、TeX Gyre Termes/Heros、Latin Modern Mono

这些文件均随本项目提供。`requirements/` 只保存赛事要求用于对照，不参与编译。

## TeX Live 通用依赖

引擎：XeLaTeX；文献处理：Biber；自动构建：latexmk。

宏包与文档类：ctexart、iftex、geometry、fontspec/xeCJK（由 ctex 加载）、indentfirst、amsmath、amssymb、amsthm、newtxmath、booktabs、tabularx、array、multirow、longtable、makecell、graphicx、caption、enumitem、xcolor、listings、biblatex、fancyhdr、hyperref、cleveref，以及这些宏包自身的依赖。数学模式还使用 TeX Live 自带的 TeX Gyre 传统字体编码支持。

这些是已安装的 TeX Live 发行版组件，不是需要另行下载的模板附件。字体文件采用本项目的 `fonts/` 相对路径加载，不依赖 Windows 专属中文字体。

## 自检

在本目录运行 `latexmk -xelatex -outdir=build main.tex`。构建记录在 `build/main.log`，实际读取文件清单在 `build/main.fls`；文献处理记录在 `build/main.blg`。

依赖及版式检查结果见 `VALIDATION.md`。
