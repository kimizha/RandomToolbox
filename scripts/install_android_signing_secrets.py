"""Run on an authorized workstation; send values to gh stdin, never stdout/argv."""
import subprocess,sys
from pathlib import Path
if len(sys.argv)!=3:raise SystemExit('Usage: python3 scripts/install_android_signing_secrets.py PRIVATE_SIGNING_DIRECTORY OWNER/REPO')
folder=Path(sys.argv[1]);repo=sys.argv[2]
names=['ANDROID_KEYSTORE_BASE64','ANDROID_KEYSTORE_PASSWORD','ANDROID_KEY_ALIAS','ANDROID_KEY_PASSWORD']
values={name:(folder/(name+'.txt')).read_text() for name in names}
if not all(values.values()):raise SystemExit('Incomplete signing kit')
for name,value in values.items():
 r=subprocess.run(['gh','secret','set',name,'--repo',repo],input=value,text=True,capture_output=True)
 if r.returncode:raise SystemExit('Unable to set '+name+'; check GitHub authentication and repository Secrets write permission (credential values omitted)')
 print('Configured '+name)
