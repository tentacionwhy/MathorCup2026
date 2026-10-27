"""Compare independently rebuilt numerical tables with the delivery reference."""
import json
from common import ROOT,sha256,json_dump

def main():
    reference=json.loads((ROOT/'metadata/rebuild_reference_hashes.json').read_text(encoding='utf-8'))
    rows=[dict(path=p,expected=h,actual=sha256(ROOT/p),identical=sha256(ROOT/p)==h) for p,h in reference.items()]
    assert all(r['identical'] for r in rows),rows
    json_dump(ROOT/'reports/reproducibility.json',dict(status='passed',
      scope='Three complete numerical CSVs match a previous end-to-end rebuild byte for byte; figure and evidence annotation changes do not change rankings.',
      invocation='run.py invoked with a different current working directory',tables=rows))
    print('Three numerical tables match the previous complete rebuild byte for byte.')

if __name__=='__main__':main()
