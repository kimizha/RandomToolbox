"""Offline certificate-anchor checks; fake keytool output, never access signing Secrets."""
import base64,contextlib,hashlib,io,os,runpy,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import verify_signed_apk
ROOT=Path(__file__).resolve().parents[1]
class ProbeSigningChecks(unittest.TestCase):
 def execute(self,matching):
  with tempfile.TemporaryDirectory() as directory:
   destination=Path(directory)/'github-env';cert=b'public-certificate-fixture'
   env={'ANDROID_KEYSTORE_BASE64':base64.b64encode(b'non-key-fixture').decode(),'ANDROID_KEYSTORE_PASSWORD':'fixture','ANDROID_KEY_ALIAS':'fixture','ANDROID_KEY_PASSWORD':'fixture','HAPPYBOX_SECURITY_PROBE_TEST':'1','GITHUB_REF':'refs/heads/ui/android-happybox-redesign','GITHUB_RUN_NUMBER':'161','RUNNER_TEMP':directory,'GITHUB_ENV':str(destination)}
   expected=hashlib.sha256(cert).hexdigest() if matching else '0'*64
   with patch.dict(os.environ,env,clear=True),patch('subprocess.run',return_value=SimpleNamespace(returncode=0,stdout=cert)),patch.object(verify_signed_apk,'PROBE_CERT_SHA256',expected),contextlib.redirect_stdout(io.StringIO()):
    if matching:
     runpy.run_path(str(ROOT/'scripts/prepare_ci_signing.py'),run_name='__main__')
     self.assertIn('ANDROID_VERSION_CODE=100161',destination.read_text())
    else:
     with self.assertRaisesRegex(SystemExit,'stopping before build'):runpy.run_path(str(ROOT/'scripts/prepare_ci_signing.py'),run_name='__main__')
     self.assertFalse(destination.exists())
 def test_matching_certificate_proceeds(self):self.execute(True)
 def test_changed_certificate_stops_before_build(self):self.execute(False)
if __name__=='__main__':unittest.main()
