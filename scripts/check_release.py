"""Offline tests for APK identity checks and UI-only publication; no GitHub writes."""
import contextlib,hashlib,importlib.util,io,json,os,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
def load(name):
 spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
verify=load('verify_signed_apk');publish=load('publish_ui_release')
class ReleaseChecks(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.old=Path.cwd();os.chdir(self.root)
  self.addCleanup(os.chdir,self.old);self.addCleanup(self.tmp.cleanup)
  p=Path('app/build/outputs/apk/debug');p.mkdir(parents=True)
  with zipfile.ZipFile(p/'app-debug.apk','w') as z:z.writestr('assets/index.html','<html>Offline fixture</html>')
  Path('app/build.gradle').write_text("versionName '2.7'")
  self.cert=b'public test certificate';self.fingerprint=hashlib.sha256(self.cert).hexdigest()
  self.env={'ANDROID_HOME':'/test-sdk','ANDROID_KEYSTORE_FILE':'/not-read.p12','ANDROID_KEY_ALIAS':'test','ANDROID_KEYSTORE_PASSWORD':'SIGNING_SECRET_NEVER_PRINT','ANDROID_VERSION_CODE':'100321','GITHUB_SHA':'a'*40,'GITHUB_REF_NAME':'ui/android-happybox-redesign','GITHUB_REF':'refs/heads/ui/android-happybox-redesign','GITHUB_REPOSITORY':'test/repo','GITHUB_RUN_ID':'123','RUNNER_TEMP':str(self.root),'RT_STABLE_SIGNING':'true','HAPPYBOX_SECURITY_PROBE_TEST':'0','HAPPYBOX_DATA_PROTECTION_TEST':'0','RT_PREVIOUS_APK_ARTIFACT_ID':'','RT_PREVIOUS_APK_RELEASE_TAG':''}
  self.pkg='com.randomtoolbox.app';self.code='100321';self.actual_cert=self.fingerprint
 def fake_run(self,args,**kwargs):
  command=Path(args[0]).name
  if command=='apksigner':return f'Signer #1 certificate SHA-256 digest: {self.actual_cert}\n'
  if command=='aapt':return f"package: name='{self.pkg}' versionCode='{self.code}' versionName='2.7'\napplication-debuggable\n"
  if command=='keytool':return self.cert
  raise AssertionError(command)
 def execute(self):
  output=io.StringIO()
  with patch.dict(os.environ,self.env),patch.object(verify,'run',self.fake_run),patch.object(verify,'PROBE_CERT_SHA256',getattr(self,'probe_anchor',self.fingerprint)),contextlib.redirect_stdout(output):verify.main()
  return output.getvalue()
 def test_public_metadata_only(self):
  out=self.execute();report=json.loads(Path('release-output/verification.json').read_text());self.assertEqual(report['version_code'],100321);self.assertTrue(report['matches_configured_certificate']);self.assertNotIn(self.env['ANDROID_KEYSTORE_PASSWORD'],out);self.assertNotIn('ANDROID_KEYSTORE_FILE',out)
 def test_reject_unexpected_package(self):
  self.pkg='other.app'
  with self.assertRaises(SystemExit):self.execute()
 def test_reject_unexpected_version(self):
  self.code='15'
  with self.assertRaises(SystemExit):self.execute()
 def test_reject_wrong_certificate(self):
  self.actual_cert='0'*64
  with self.assertRaises(SystemExit):self.execute()
 def test_probe_mode_requires_included_entry(self):
  self.env['HAPPYBOX_SECURITY_PROBE_TEST']='1'
  with self.assertRaises(SystemExit):self.execute()
 def test_normal_mode_rejects_probe_entry(self):
  with zipfile.ZipFile('app/build/outputs/apk/debug/app-debug.apk','w') as z:z.writestr('assets/index.html','HAPPYBOX_SECURITY_PROBE_TEST_ONLY')
  with self.assertRaises(SystemExit):self.execute()
 def test_probe_rejects_changed_previous_certificate(self):
  with zipfile.ZipFile('app/build/outputs/apk/debug/app-debug.apk','w') as z:z.writestr('assets/index.html','HAPPYBOX_SECURITY_PROBE_TEST_ONLY')
  self.env['HAPPYBOX_SECURITY_PROBE_TEST']='1';self.probe_anchor='0'*64
  with self.assertRaises(SystemExit):self.execute()
 def test_main_cannot_publish(self):
  with patch.dict(os.environ,{**self.env,'GITHUB_REF':'refs/heads/main'}),self.assertRaises(SystemExit):publish.main()
 def test_probe_apk_cannot_publish_even_with_forged_report_flag(self):
  with zipfile.ZipFile('app/build/outputs/apk/debug/app-debug.apk','w') as z:z.writestr('assets/index.html','HAPPYBOX_SECURITY_PROBE_TEST_ONLY')
  self.env['HAPPYBOX_SECURITY_PROBE_TEST']='1'
  self.execute();p=Path('release-output/verification.json');report=json.loads(p.read_text());self.assertTrue(report['contains_security_probe']);report['contains_security_probe']=False;p.write_text(json.dumps(report))
  with patch.dict(os.environ,self.env),self.assertRaises(SystemExit):publish.main()
 def test_unsigned_cannot_publish(self):
  with patch.dict(os.environ,{**self.env,'RT_STABLE_SIGNING':'false'}),self.assertRaises(SystemExit):publish.main()
 def test_protection_mode_cannot_publish(self):
  self.execute()
  with patch.dict(os.environ,{**self.env,'HAPPYBOX_DATA_PROTECTION_TEST':'1'}),self.assertRaises(SystemExit):publish.main()
 def test_protection_report_cannot_publish(self):
  self.execute();path=Path('release-output/verification.json');report=json.loads(path.read_text());report['data_protection_test']=True;path.write_text(json.dumps(report))
  with patch.dict(os.environ,self.env),self.assertRaises(SystemExit):publish.main()
 def test_protection_assets_cannot_publish_with_forged_report(self):
  self.execute()
  with zipfile.ZipFile('release-output/Happybox-v2.7-code100321.apk','w') as z:z.writestr('assets/index.html','HAPPYBOX_DATA_PROTECTION_TEST_ONLY')
  with patch.dict(os.environ,self.env),self.assertRaises(SystemExit):publish.main()
 def test_normal_build_rejects_protection_assets(self):
  with zipfile.ZipFile('app/build/outputs/apk/debug/app-debug.apk','w') as z:z.writestr('assets/index.html','HAPPYBOX_DATA_PROTECTION_TEST_ONLY')
  with self.assertRaises(SystemExit):self.execute()
 def test_verified_release_targets_exact_ui_commit_and_warns_on_mismatch(self):
  self.execute();p=Path('release-output/verification.json');report=json.loads(p.read_text());report['previous_apk']={'comparison':'verified','same_certificate':False};p.write_text(json.dumps(report));calls=[]
  def fake_gh(args):
   calls.append(args)
   if args[0]=='api':return json.dumps({'html_url':'https://github.com/test/repo/releases/tag/ui-v2.7-code100321','assets':[{'name':report['apk_filename'],'browser_download_url':'https://github.com/test/repo/releases/download/ui-v2.7-code100321/'+report['apk_filename']}]})
   return ''
  class MissingRelease:returncode=1
  with patch.dict(os.environ,self.env),patch.object(publish,'gh',fake_gh),patch.object(publish.subprocess,'run',lambda *a,**k:MissingRelease()),contextlib.redirect_stdout(io.StringIO()):publish.main()
  create=calls[0];self.assertEqual(create[create.index('--target')+1],'a'*40);self.assertIn('--prerelease',create);self.assertIn('--latest=false',create);notes=Path('happybox-release-notes.md').read_text();self.assertIn('无法直接覆盖安装',notes);self.assertIn('不要直接卸载旧版',notes);self.assertIn('尚未确认真实账号',notes);self.assertNotIn(self.env['ANDROID_KEYSTORE_PASSWORD'],notes)
if __name__=='__main__':unittest.main()
