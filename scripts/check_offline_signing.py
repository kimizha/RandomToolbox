"""Fail closed against the certificate of delivered 100160/100161 APKs."""
import hashlib,os,subprocess
from verify_signed_apk import PROBE_CERT_SHA256
r=subprocess.run(['keytool','-exportcert','-keystore',os.environ['ANDROID_KEYSTORE_FILE'],'-alias',os.environ['ANDROID_KEY_ALIAS'],'-storepass:env','ANDROID_KEYSTORE_PASSWORD'],capture_output=True)
if r.returncode or hashlib.sha256(r.stdout).hexdigest()!=PROBE_CERT_SHA256:raise SystemExit('Fixed certificate mismatch; no APK distribution allowed')
print('Fixed certificate matches delivered APKs:',PROBE_CERT_SHA256)
