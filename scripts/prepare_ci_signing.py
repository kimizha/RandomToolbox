"""Require a stable private key for distributable APKs; never generate a throwaway key."""
import base64,os,subprocess
from pathlib import Path
names=['ANDROID_KEYSTORE_BASE64','ANDROID_KEYSTORE_PASSWORD','ANDROID_KEY_ALIAS','ANDROID_KEY_PASSWORD']
values={name:os.environ.get(name,'') for name in names}
provided=sum(bool(v) for v in values.values())
if provided and provided!=len(names):raise SystemExit('Incomplete Android signing Secrets; all four are required')
version=100000+int(os.environ.get('GITHUB_RUN_NUMBER','0'))
if version>2147483647:raise SystemExit('Android versionCode exceeds the platform limit')
output=['ANDROID_VERSION_CODE='+str(version)]
if not provided:
 output.append('RT_STABLE_SIGNING=false')
 print('Stable signing Secrets are not configured. Compile checks only; no temporary-key APK will be published.')
else:
 try:raw=base64.b64decode(''.join(values['ANDROID_KEYSTORE_BASE64'].split()),validate=True)
 except Exception:raise SystemExit('Invalid keystore encoding; check ANDROID_KEYSTORE_BASE64')
 path=Path(os.environ['RUNNER_TEMP'])/'happybox-stable-signing.p12'
 path.write_bytes(raw);path.chmod(0o600)
 result=subprocess.run(['keytool','-list','-keystore',str(path),'-alias',values['ANDROID_KEY_ALIAS'],'-storepass:env','ANDROID_KEYSTORE_PASSWORD'],capture_output=True)
 if result.returncode:raise SystemExit('Cannot open Android signing key; verify the signing Secrets (credentials omitted)')
 output+=['ANDROID_KEYSTORE_FILE='+str(path),'RT_STABLE_SIGNING=true']
 print('Stable Android signing key validated (credentials omitted).')
with open(os.environ['GITHUB_ENV'],'a',encoding='utf-8') as f:f.write('\n'.join(output)+'\n')
