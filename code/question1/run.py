"""One-command rebuild from this folder's copied raw data; works from any CWD."""
from pathlib import Path
import argparse
import os
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--skip-compile',action='store_true',help='Generate LaTeX without requiring XeLaTeX')
    parser.add_argument('--verify-only',action='store_true')
    args=parser.parse_args()
    env=os.environ.copy();env['PYTHONIOENCODING']='utf-8'
    if args.verify_only:
        subprocess.run([sys.executable,str(ROOT/'scripts/verify_outputs.py')],cwd=ROOT,env=env,check=True);return
    stages=['prepare','features','ranking','sensitivity','process_analysis','plot_results','write_report']
    start=time.time()
    for stage in stages:
        print(f'\n[{stage}]',flush=True)
        log=ROOT/'logs'/f'{stage}.log'
        run=subprocess.run([sys.executable,str(ROOT/'scripts'/f'{stage}.py')],cwd=ROOT,env=env,
          stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
        log.write_text(run.stdout,encoding='utf-8');print(run.stdout,flush=True)
        if run.returncode:raise SystemExit(run.returncode)
    tests=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=ROOT,env=env,
      stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
    (ROOT/'logs/tests.log').write_text(tests.stdout,encoding='utf-8');print(tests.stdout,flush=True)
    if tests.returncode:raise RuntimeError('Boundary tests failed; see logs/tests.log')
    if not args.skip_compile:
        exe=shutil.which('xelatex')
        if exe:
            for _ in range(2):
                run=subprocess.run([exe,'-interaction=nonstopmode','-halt-on-error','main.tex'],cwd=ROOT/'manuscript',env=env,
                   stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
                (ROOT/'logs/xelatex.log').write_text(run.stdout,encoding='utf-8')
                if run.returncode:raise RuntimeError('XeLaTeX failed; see logs/xelatex.log')
        else:print('XeLaTeX unavailable: analysis/figures/LaTeX source completed; install XeLaTeX to compile PDF.',flush=True)
    subprocess.run([sys.executable,str(ROOT/'scripts/verify_outputs.py')],cwd=ROOT,env=env,check=True)
    print(f'Finished in {time.time()-start:.1f}s. See reports and manuscript.',flush=True)

if __name__=='__main__':main()
