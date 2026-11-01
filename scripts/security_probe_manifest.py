"""Build-time evidence for local source/package only; never attests remote deployment."""
import hashlib,re,zipfile
from pathlib import Path
def create_manifest(root):
 root=Path(root);source=root/'cloudfunctions/happyboxSecurityProbe'
 archive=root/'deployment/security-probe/HappyboxSecurityProbe-readonly-tx-null-v2.zip'
 files={name:hashlib.sha256((source/name).read_bytes()).hexdigest() for name in ('index.js','probe.cjs','transaction-read.cjs','package.json','package-lock.json')}
 with zipfile.ZipFile(archive) as z:
  for name,digest in files.items():
   if z.namelist().count(name)!=1 or hashlib.sha256(z.read(name)).hexdigest()!=digest:raise ValueError('Probe package/source mismatch: '+name)
 revision=re.search(r"const REVISION='([^']+)'",(source/'probe.cjs').read_text()).group(1)
 return {'revision':revision,'packageSha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'files':files,'localSourceCheck':'MATCH'}
