"""Inspect final release assets, music identity and absence of account bundles."""
import os,zipfile,hashlib,json
from pathlib import Path
with zipfile.ZipFile(os.environ['RT_APK_PATH']) as z:
 # Android ZIP writers may store UTF-8 path bytes without setting the UTF-8 flag.
 # Python then exposes those bytes as CP437; normalize names only for comparison.
 def decoded(info):
  if info.flag_bits & 0x800:return info.filename
  try:return info.filename.encode('cp437').decode('utf-8')
  except (UnicodeEncodeError,UnicodeDecodeError):return info.filename
 entries={decoded(i):i for i in z.infolist()}
 assert len(entries)==len(z.infolist()), 'Ambiguous normalized ZIP paths'
 names=list(entries)
 assert not any('cloudbase' in n.lower() or 'dev-security-probe' in n or 'probe-context' in n for n in names)
 for n in names:
  if n.startswith('assets/') and n.endswith(('.html','.js')):
   s=z.read(entries[n]).decode()
   assert not any(x in s for x in ['RT_AUTH_NATIVE_V3','RTCloudbaseSDK','rtSyncLocalChanged','rtLoggedIn','rtShowLogin','happyboxSecurityProbe']),n
 for f in Path('app/src/main/assets/music').glob('*.mp3'):
  assert z.read(entries['assets/music/'+f.name])==f.read_bytes(),f.name
 assert 'assets/ui/local-backup.js' in names and 'assets/ui/offline.js' in names
print('APK offline asset isolation and all six original music files verified')

from verify_signed_apk import PROBE_CERT_SHA256
report=json.loads(Path('release-output/verification.json').read_text())
assert report['certificate_sha256']==PROBE_CERT_SHA256
assert report['version_code']>100161 and report['package_name']=='com.randomtoolbox.app'
assert not report['debuggable'], 'Candidate must use release variant'
previous=report.get('previous_apk',{})
if previous.get('comparison')=='verified':assert previous.get('same_certificate'), 'Prior APK certificate mismatch; stop distribution'
print('Release candidate identity and overwrite certificate checks passed')
