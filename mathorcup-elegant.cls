\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{mathorcup-elegant}[2026/10/25 MathorCup 2026 with ElegantPaper typography]
% Contest structure follows the supplied 2026 rules; typography inspired by ElegantPaper.
\RequirePackage{iftex}
\ifXeTeX\else\ClassError{mathorcup-elegant}{Use XeLaTeX}{Compile with latexmk -xelatex.}\fi
\PassOptionsToPackage{no-math}{fontspec}
\LoadClass[UTF8,fontset=none,scheme=plain,a4paper,11pt,oneside]{ctexart}
\RequirePackage[left=1in,right=1in,top=1in,bottom=1in,headheight=0pt,headsep=0pt,footskip=25pt]{geometry}
\setmainfont{texgyretermes}[Path=fonts/,Extension=.otf,UprightFont=*-regular,BoldFont=*-bold,ItalicFont=*-italic,BoldItalicFont=*-bolditalic]
\setsansfont{texgyreheros}[Path=fonts/,Extension=.otf,UprightFont=*-regular,BoldFont=*-bold,ItalicFont=*-italic,BoldItalicFont=*-bolditalic,Scale=0.9]
\setmonofont{lmmono10-regular.otf}[Path=fonts/]
\setCJKmainfont{FandolSong-Regular.otf}[Path=fonts/,BoldFont=FandolSong-Bold.otf,ItalicFont=FandolKai-Regular.otf]
\setCJKsansfont{FandolHei-Regular.otf}[Path=fonts/,BoldFont=FandolHei-Bold.otf]
\setCJKmonofont{FandolFang-Regular.otf}[Path=fonts/]
\setCJKfamilyfont{zhsong}{FandolSong-Regular.otf}[Path=fonts/]
\setCJKfamilyfont{zhhei}{FandolHei-Regular.otf}[Path=fonts/]
\setCJKfamilyfont{zhkai}{FandolKai-Regular.otf}[Path=fonts/]
\setCJKfamilyfont{zhfs}{FandolFang-Regular.otf}[Path=fonts/]
\linespread{1.35}
\setlength{\parindent}{2em}
\setlength{\parskip}{0pt plus 1pt}
\RequirePackage{indentfirst}
\ctexset{
  section={format=\Large\bfseries\raggedright,name={},number=\arabic{section},aftername=\quad,beforeskip=2.2ex plus .5ex,afterskip=1.1ex plus .2ex},
  subsection={format=\large\bfseries\raggedright,name={},number=\thesection.\arabic{subsection},aftername=\quad,beforeskip=1.8ex plus .4ex,afterskip=.8ex plus .2ex},
  subsubsection={format=\normalsize\bfseries\raggedright,name={},number=\thesubsection.\arabic{subsubsection},aftername=\quad,beforeskip=1.4ex plus .3ex,afterskip=.6ex plus .2ex}}
\RequirePackage{amsmath,amssymb,amsthm}
\RequirePackage{newtxmath}
% Legacy math alphabets use TeX Gyre's matching TeX encodings.
\SetSymbolFont{operators}{normal}{OT1}{qtm}{m}{n}
\SetSymbolFont{operators}{bold}{OT1}{qtm}{b}{n}
\SetMathAlphabet{\mathbf}{normal}{OT1}{qtm}{b}{n}
\SetMathAlphabet{\mathbf}{bold}{OT1}{qtm}{b}{n}
\SetMathAlphabet{\mathit}{normal}{OT1}{qtm}{m}{it}
\SetMathAlphabet{\mathit}{bold}{OT1}{qtm}{b}{it}
\SetMathAlphabet{\mathsf}{normal}{OT1}{qhv}{m}{n}
\SetMathAlphabet{\mathsf}{bold}{OT1}{qhv}{b}{n}
\RequirePackage{booktabs,tabularx,array,multirow,longtable,makecell}
\newcolumntype{Y}{>{\centering\arraybackslash}X}
\RequirePackage{graphicx}
\graphicspath{{figures/}}
\RequirePackage{caption}
\renewcommand{\figurename}{图}
\renewcommand{\tablename}{表}
\captionsetup{font=small,labelfont=bf,labelsep=quad}
\captionsetup[figure]{skip=3pt}
\captionsetup[table]{skip=3pt,position=top}
\RequirePackage{enumitem}
\setlist{nosep,leftmargin=2em}
\RequirePackage{xcolor,listings}
\renewcommand{\lstlistingname}{代码}
\definecolor{codecomment}{RGB}{0,100,0}
\lstset{basicstyle=\small\ttfamily,breaklines=true,columns=fullflexible,keepspaces=true,showstringspaces=false,frame=none,numbers=left,numberstyle=\scriptsize\color{gray},numbersep=9pt,tabsize=4,keywordstyle=\color{blue!60!black},commentstyle=\color{codecomment},stringstyle=\color{purple!60!black}}
\lstnewenvironment{python}[1][]{\lstset{language=Python,#1}}{}
\lstnewenvironment{matlab}[1][]{\lstset{language=Matlab,#1}}{}
\RequirePackage[backend=biber,style=mathorcup2026,sorting=none,sortcites=false,maxbibnames=99,giveninits=false,url=true,doi=false,isbn=false]{biblatex}
\RequirePackage{fancyhdr}
\fancypagestyle{contestbody}{\fancyhf{}\fancyfoot[C]{\normalfont\small\thepage}\renewcommand{\headrulewidth}{0pt}\renewcommand{\footrulewidth}{0pt}}
\fancypagestyle{plain}{\fancyhf{}\fancyfoot[C]{\normalfont\small\thepage}\renewcommand{\headrulewidth}{0pt}\renewcommand{\footrulewidth}{0pt}}
\pagestyle{empty}
\RequirePackage[unicode,hidelinks,bookmarksnumbered=true,bookmarksopen=true]{hyperref}
\hypersetup{pdfauthor={},pdfcreator={LaTeX},pdfsubject={}}
\RequirePackage[nameinlink,noabbrev]{cleveref}
\crefname{figure}{图}{图}\crefname{table}{表}{表}\crefname{equation}{式}{式}\crefname{section}{节}{节}
\renewcommand{\contentsname}{目录}
\setcounter{tocdepth}{2}
\setcounter{secnumdepth}{3}
\newcommand{\@bianhao}{待填写}
\newcommand{\@tihao}{A/B}
\newcommand{\@timu}{论文题目（请替换）}
\newcommand{\@keyword}{关键词一；关键词二；关键词三}
\newcommand{\bianhao}[1]{\gdef\@bianhao{#1}}
\newcommand{\tihao}[1]{\gdef\@tihao{#1}}
\newcommand{\timu}[1]{\gdef\@timu{#1}}
\newcommand{\keyword}[1]{\gdef\@keyword{#1}}
\newcommand{\ee}{\mathrm{e}}\newcommand{\ii}{\mathrm{i}}
% Cover and contents occupy physical pages 1 and 2, without printed numbers.
\renewenvironment{abstract}{%
  \hypersetup{pageanchor=false}\pagenumbering{gobble}\pagestyle{empty}\thispagestyle{empty}
  \pdfbookmark[0]{摘要}{contest-abstract}
  \begin{center}
    \renewcommand{\arraystretch}{1.25}
    \begin{tabularx}{.62\textwidth}{|Y|Y|}\hline
      队伍编号 & \@bianhao\\\hline
      赛道 & \@tihao\\\hline
    \end{tabularx}\par\vspace{1.4em}
    {\Large\bfseries\@timu\par}\vspace{.8em}
    {\large\bfseries 摘\quad 要\par}
  \end{center}\vspace{.2em}\noindent\ignorespaces
}{%
  \par\vspace{.8em}\noindent\textbf{关键词：}\@keyword\par
  \ifnum\value{page}>1\ClassError{mathorcup-elegant}{Abstract exceeds one page}{Shorten the abstract so the contents is on physical page 2.}\fi
  \clearpage
}
\newcommand{\makecontestcontents}{%
  \ifnum\value{page}=2\else\ClassError{mathorcup-elegant}{Contents must start on physical page 2}{Use one abstract page followed by makecontestcontents.}\fi
  \pagestyle{empty}\thispagestyle{empty}
  \pdfbookmark[0]{目录}{contest-contents}
  \tableofcontents\thispagestyle{empty}
  \ifnum\value{page}>2\ClassError{mathorcup-elegant}{Contents exceeds one page}{Reduce tocdepth or shorten headings to keep the contents on page 2.}\fi
  \clearpage\pagenumbering{arabic}\hypersetup{pageanchor=true}\pagestyle{contestbody}
}
\newcommand{\printcontestbibliography}{\printbibliography[heading=bibintoc,title={参考文献}]}
\newcommand{\contestappendix}{%
  \clearpage
  \ifnum\value{page}>31\ClassWarningNoLine{mathorcup-elegant}{Main matter exceeds 30 pages; review the contest limit}\fi
  \appendix
  \ctexset{section={name={附录\space,},number=\Alph{section}}}
}
\endinput
