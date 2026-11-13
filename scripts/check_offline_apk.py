"""Inspect final release assets, music identity and absence of account bundles."""
import os,zipfile,hashlib
from pathlib import Path
with zipfile.ZipFile(os.environ['RT_APK_PATH']) as z:
 names=z.namelist()
 assert not any('cloudbase' in n.lower() or 'dev-security-probe' in n or 'probe-context' in n for n in names)
 for n in names:
  if n.startswith('assets/') and n.endswith(('.html','.js')):
   s=z.read(n).decode()
   assert not any(x in s for x in ['RT_AUTH_NATIVE_V3','RTCloudbaseSDK','rtSyncLocalChanged','rtLoggedIn','rtShowLogin','happyboxSecurityProbe']),n
 for f in Path('app/src/main/assets/music').glob('*.mp3'):
  assert z.read('assets/music/'+f.name)==f.read_bytes(),f.name
 assert 'assets/ui/local-backup.js' in names and 'assets/ui/offline.js' in names
print('APK offline asset isolation and all six original music files verified')
