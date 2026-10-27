"""Create a portable archive of code, required inputs and completed results."""
from pathlib import Path
import zipfile
import json
import hashlib
from common import ROOT,sha256,json_dump

def main():
    destination=ROOT.parent/(ROOT.name+'.zip')
    exclude={'.venv','__pycache__','source_zarr_chunks','tmp'}
    files=[p for p in ROOT.rglob('*') if p.is_file()
           and p.relative_to(ROOT).as_posix()!='reports/package_summary.json'
           and not any(part in exclude for part in p.relative_to(ROOT).parts)]
    with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(files):z.write(p,arcname=ROOT.name+'/'+p.relative_to(ROOT).as_posix())
    manifest=json.loads((ROOT/'metadata/input_manifest.json').read_text(encoding='utf-8'))
    with zipfile.ZipFile(destination) as z:
        assert z.testzip() is None
        assert all(not n.startswith(('/','\\')) and '..' not in Path(n).parts for n in z.namelist())
        for entry in manifest:
            name=ROOT.name+'/'+entry['path'].replace('\\','/')
            assert hashlib.sha256(z.read(name)).hexdigest()==entry['sha256'],name
    json_dump(ROOT/'reports/package_summary.json',dict(archive_name=destination.name,
      archive_bytes=destination.stat().st_size,archive_sha256=sha256(destination),
      file_count=len(files),excluded=sorted(exclude),archive_integrity='CRC and all 46 input SHA256 hashes passed',
      note='All 46 manifest inputs included; environment/cache excluded'))
    print(destination.name,destination.stat().st_size,'bytes;',len(files),'files',flush=True)

if __name__=='__main__':main()
