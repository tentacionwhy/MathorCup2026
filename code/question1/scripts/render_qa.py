"""Render the compiled manuscript with Python and record layout/source QA."""
import json
from pathlib import Path
import pymupdf
from PIL import Image,ImageOps,ImageDraw
from common import ROOT,json_dump

def main():
    doc=pymupdf.open(ROOT/'manuscript/main.pdf')
    target=ROOT/'tmp/pdf_preview';target.mkdir(exist_ok=True)
    thumbs=[];pages=[]
    for i,page in enumerate(doc):
        pix=page.get_pixmap(matrix=pymupdf.Matrix(1.4,1.4),alpha=False)
        path=target/f'page_{i+1}.png';pix.save(path)
        im=Image.open(path).convert('RGB');im.thumbnail((500,710))
        canvas=Image.new('RGB',(520,750),'#ECEFF2');canvas.paste(im,((520-im.width)//2,22))
        ImageDraw.Draw(canvas).text((12,728),f'Page {i+1}',fill='black');thumbs.append(canvas)
        pages.append(dict(page=i+1,characters=len(page.get_text()),image_file=str(path.relative_to(ROOT))))
    sheet=Image.new('RGB',(520*3,750*((len(thumbs)+2)//3)),'white')
    for i,im in enumerate(thumbs):sheet.paste(im,((i%3)*520,(i//3)*750))
    sheet.save(target/'contact_sheet.png')
    log=(ROOT/'manuscript/main.log').read_text(encoding='utf-8',errors='replace')
    json_dump(ROOT/'reports/pdf_qa.json',dict(pages=len(doc),page_details=pages,
      overfull_boxes=log.count('Overfull'),undefined_references='undefined references' in log,
      qa_note='Rendered with Python/PyMuPDF; final image inspection recorded separately'))
    print('Rendered',len(doc),'pages; overfull boxes',log.count('Overfull'),flush=True)

if __name__=='__main__':main()
