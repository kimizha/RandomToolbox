"""Package reviewed probe source and locked public npm dependencies; no cloud or APK action."""
import hashlib,json,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path(sys.argv[3]).resolve() if len(sys.argv)==4 else ROOT/'cloudfunctions/happyboxSecurityProbe'
FILES=('index.js','probe.cjs','transaction-read.cjs','package.json','package-lock.json')
if len(sys.argv) not in (3,4):raise SystemExit('Usage: package_security_probe.py locked-dependency-directory output.zip [source-directory]')
if (SOURCE/'read-control.cjs').exists():FILES+=('read-control.cjs',)
deps=Path(sys.argv[1]);out=Path(sys.argv[2])
if (deps/'package-lock.json').read_bytes()!=(SOURCE/'package-lock.json').read_bytes():raise SystemExit('Dependency lock mismatch')
for package,version in [('@cloudbase/node-sdk','4.2.1'),('axios','1.21.0')]:
 if json.loads((deps/'node_modules'/package/'package.json').read_text())['version']!=version:raise SystemExit('Installed dependency version mismatch')
out.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
 paths=[(SOURCE/f,f) for f in FILES]
 paths += [(p,p.relative_to(deps).as_posix()) for p in sorted((deps/'node_modules').rglob('*')) if p.is_file() and not p.is_symlink()]
 for path,name in paths:
  entry=zipfile.ZipInfo(name,date_time=(2026,1,1,0,0,0));entry.compress_type=zipfile.ZIP_DEFLATED;entry.external_attr=0o100644<<16
  z.writestr(entry,path.read_bytes())
with zipfile.ZipFile(out) as z:
 for name in FILES:
  if z.read(name)!=(SOURCE/name).read_bytes():raise SystemExit('Archive/source mismatch')
digest=hashlib.sha256(out.read_bytes()).hexdigest()
out.with_suffix('.sha256').write_text(digest+'  '+out.name+'\n')
print('Package bytes:',out.stat().st_size);print('SHA256:',digest)
