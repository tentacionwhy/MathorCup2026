"""Check the scoped Q1 import and render the formal paper for visual review."""
from pathlib import Path
import hashlib
import json
import re
import pymupdf
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]

def main():
    manifest=json.loads((ROOT/'writing/question1_import_manifest.json').read_text(encoding='utf-8'))
    for entry in manifest['copied_files']:
        path=ROOT/entry['path']
        assert path.is_file(),entry['path']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256'],entry['path']
    chapter=(ROOT/'sections/03-factors.tex').read_text(encoding='utf-8')
    assert chapter.count('\\subsection{')==5
    assert chapter.count('\\includegraphics')==5
    assert chapter.count('\\input{tables/question1/')==3
    assert '\\writingplaceholder' not in chapter and '\\begin{thebibliography}' not in chapter
    assert not re.search(r'[A-Za-z]:[\\/]',chapter)
    tables=[(ROOT/'tables/question1'/name).read_text(encoding='utf-8')
       for name in ['candidate_groups.tex','group_comparison.tex','top5_evidence.tex']]
    for t in tables:assert '\\caption{' in t and '\\label{' in t
    log=(ROOT/'build/main.log').read_text(encoding='utf-8',errors='replace')
    errors=['Overfull','undefined references','undefined on input line','Missing character:']
    assert not any(e in log for e in errors),[e for e in errors if e in log]
    doc=pymupdf.open(ROOT/'build/main.pdf')
    texts=[p.get_text() for p in doc]
    assert 'MCB2600006' in texts[0] and '目录' in texts[1]
    text='\n'.join(texts)
    assert 'Srivastava' in text and 'Unravelling' in text
    assert all(s not in text for s in ['张某某','示例期刊','samplearticle'])
    aux=(ROOT/'build/main.aux').read_text(encoding='utf-8')
    for key in ['tab:q1:candidates','tab:q1:comparison','tab:q1:top5',
       'fig:q1:structure','fig:q1:energy','fig:q1:water','fig:q1:historical','fig:q1:ranking']:
        assert '\\newlabel{'+key+'}' in aux,key
    output=ROOT/'build/question1_review';output.mkdir(parents=True,exist_ok=True)
    thumbs=[]
    for i,p in enumerate(doc):
        pix=p.get_pixmap(matrix=pymupdf.Matrix(1.5,1.5),alpha=False)
        file=output/f'page_{i+1:02d}.png';pix.save(file)
        im=Image.open(file).convert('RGB');im.thumbnail((390,555))
        thumb=Image.new('RGB',(410,590),'#EFF1F4');thumb.paste(im,((410-im.width)//2,8))
        ImageDraw.Draw(thumb).text((12,566),f'Physical page {i+1}',fill='black');thumbs.append(thumb)
    sheet=Image.new('RGB',(410*4,590*((len(thumbs)+3)//4)),'white')
    for i,im in enumerate(thumbs):sheet.paste(im,((i%4)*410,(i//4)*590))
    sheet.save(output/'contact_sheet.png')
    checks=dict(copied_files_sha256=len(manifest['copied_files']),q1_subsections=5,main_figures=5,
      editable_tables=3,all_references_resolved=True,overfull_boxes=0,
      total_physical_pages=len(doc),cover_and_single_contents_preserved=True,
      page_footers=[dict(physical_page=i+1,last_text_line=t.strip().splitlines()[-1]) for i,t in enumerate(texts)],
      copied_data_and_code='code/question1; project-relative; no external data dependency',
      qa_preview='build/question1_review/contact_sheet.png')
    (ROOT/'writing/question1_import_validation.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(checks,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
