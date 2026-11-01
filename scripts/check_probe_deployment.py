"""Compare a console-downloaded function ZIP with reviewed source; never extract or execute it."""
import hashlib,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'cloudfunctions/happyboxSecurityProbe'
FILES=('index.js','probe.cjs','package.json','package-lock.json','transaction-read.cjs')
if len(sys.argv)!=2:raise SystemExit('Usage: python3 scripts/check_probe_deployment.py console-code.zip')
with zipfile.ZipFile(sys.argv[1]) as z:
 names=z.namelist()
 if len(names)!=len(set(names)):raise SystemExit('Duplicate ZIP paths; comparison refused')
 candidates=[n[:-len('probe.cjs')] for n in names if (n=='probe.cjs' or n.endswith('/probe.cjs')) and 'node_modules' not in Path(n).parts]
 if len(candidates)!=1:raise SystemExit('Function source directory is ambiguous or missing')
 matched=True
 for name in FILES:
  path=candidates[0]+name
  if path not in names or z.getinfo(path).file_size>1024*1024:
   print(name+': MISSING_OR_TOO_LARGE');matched=False;continue
  match=hashlib.sha256(z.read(path)).digest()==hashlib.sha256((ROOT/name).read_bytes()).digest()
  print(name+(': MATCH' if match else ': DIFFERENT'));matched &= match
 if not matched:raise SystemExit(1)
print('Reviewed source files match. Console environment, traffic routing and installed dependencies still require verification.')
