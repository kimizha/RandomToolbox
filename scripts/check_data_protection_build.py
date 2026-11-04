"""Offline source/signing/baseline checks. No real key, GitHub request, or CloudBase access."""
import base64, contextlib, hashlib, io, os, runpy, shutil, subprocess, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import data_protection_build as protection
import verify_signed_apk

ROOT=Path(__file__).resolve().parents[1]

class ProtectionBuildChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name)
        (cls.root/'app/src/main/assets').mkdir(parents=True)
        shutil.copy(ROOT/'app/src/main/assets/index.html',cls.root/'app/src/main/assets/index.html')
        shutil.copytree(ROOT/'scripts',cls.root/'scripts')
        shutil.copytree(ROOT/'app/src/main/java',cls.root/'app/src/main/java')
        shutil.copy(ROOT/'app/build.gradle',cls.root/'app/build.gradle')
        subprocess.run(['python3','scripts/inject_auth.py'],cwd=cls.root,env={**os.environ,'CLOUDBASE_PUBLISHABLE_KEY':'eyJ-offline-fixture','HAPPYBOX_DATA_PROTECTION_TEST':'1','HAPPYBOX_SECURITY_PROBE_TEST':'0'},capture_output=True,check=True)
        cls.html=(cls.root/'app/src/main/assets/index.html').read_text()
        for name in ['cloudfunctions','deployment']:shutil.copytree(ROOT/name,cls.root/name)
        (cls.root/'app/src/main/assets/index.html').write_text((ROOT/'app/src/main/assets/index.html').read_text())
        subprocess.run(['python3','scripts/inject_auth.py'],cwd=cls.root,env={**os.environ,'CLOUDBASE_PUBLISHABLE_KEY':'eyJ-offline-fixture','HAPPYBOX_DATA_PROTECTION_TEST':'0','HAPPYBOX_SECURITY_PROBE_TEST':'1'},capture_output=True,check=True)
        cls.probe_html=(cls.root/'app/src/main/assets/index.html').read_text()
        (cls.root/'app/src/main/assets/index.html').write_text(cls.html)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def previous(self,**changes):
        return dict(package_name='com.randomtoolbox.app',version_code=100160,certificate_sha256=protection.PROBE_CERT_SHA256,apk_sha256=protection.PRIOR_APK_SHA256,**changes)
    def test_source_preserves_storage_and_package(self):protection.validate_source(self.root)
    def test_full_protection_and_profile_sources_are_bundled(self):protection.validate_assets(self.html,self.root)
    def test_probe_and_protection_assets_are_bundled(self):protection.validate_assets(self.probe_html,self.root,probe=True)
    def test_probe_missing_actual_sdk_attachment_rejected(self):
        with self.assertRaises(SystemExit):protection.validate_assets(self.probe_html.replace('window.hbAttachProbeContext({app,auth:rtAuth,','window.otherContext({app,auth:rtAuth,'),self.root,probe=True)
    def test_probe_without_pause_rejected(self):
        with self.assertRaises(SystemExit):protection.validate_assets(self.probe_html.replace('const RT_SYNC_CLOUD_PAUSED=true;','const RT_SYNC_CLOUD_PAUSED=false;'),self.root,probe=True)
    def test_probe_without_backup_rejected(self):
        with self.assertRaises(SystemExit):protection.validate_assets(self.probe_html.replace((self.root/'scripts/local-backup.js').read_text(),''),self.root,probe=True)
    def test_ui_does_not_guess_authentication_globals(self):
        for name in ['dev-security-probe.js','probe-context.js']:
            source=(ROOT/'scripts'/name).read_text();self.assertNotIn('rtCloudApp',source);self.assertNotIn('rtAuth',source)
    def test_tampered_guard_rejected(self):
        with self.assertRaises(SystemExit):protection.validate_assets(self.html.replace('const RT_SYNC_CLOUD_PAUSED=true;','const RT_SYNC_CLOUD_PAUSED=false;'),self.root)
    def test_missing_backup_rejected(self):
        with self.assertRaises(SystemExit):protection.validate_assets(self.html.replace((self.root/'scripts/local-backup.js').read_text(),''),self.root)
    def test_probe_inclusion_rejected(self):
        with self.assertRaises(SystemExit):protection.validate_assets(self.html+'HAPPYBOX_SECURITY_PROBE_TEST_ONLY',self.root)
    def test_unmarked_build_rejected(self):
        with self.assertRaises(SystemExit):protection.validate_assets(self.html.replace(protection.MARKER,''),self.root)
    def test_changed_nickname_logic_rejected(self):
        with self.assertRaises(SystemExit):protection.validate_assets(self.html.replace('function rtProfileGet(){','function changedProfileGet(){'),self.root)
    def test_duplicate_sync_implementation_rejected(self):
        with self.assertRaises(SystemExit):protection.validate_assets(self.html+'function rtSyncTick(){}',self.root)
    def test_baseline_can_cover(self):protection.validate_previous(self.previous(),100161,protection.PROBE_CERT_SHA256)
    def test_changed_fixed_certificate_rejected(self):
        with self.assertRaises(SystemExit):protection.validate_previous(self.previous(),100161,'0'*64)
    def test_different_previous_package_rejected(self):
        previous=self.previous();previous['package_name']='other.app'
        with self.assertRaises(SystemExit):protection.validate_previous(previous,100161,protection.PROBE_CERT_SHA256)
    def test_different_previous_certificate_rejected(self):
        previous=self.previous();previous['certificate_sha256']='0'*64
        with self.assertRaises(SystemExit):protection.validate_previous(previous,100161,protection.PROBE_CERT_SHA256)
    def test_different_previous_digest_rejected(self):
        previous=self.previous();previous['apk_sha256']='0'*64
        with self.assertRaises(SystemExit):protection.validate_previous(previous,100161,protection.PROBE_CERT_SHA256)
    def test_version_not_increasing_rejected(self):
        with self.assertRaises(SystemExit):protection.validate_previous(self.previous(),100160,protection.PROBE_CERT_SHA256)
    def prepare(self,anchor=None,**changes):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'github-env';certificate=b'public-certificate-fixture'
            env={'ANDROID_KEYSTORE_BASE64':base64.b64encode(b'not-a-real-key').decode(),'ANDROID_KEYSTORE_PASSWORD':'fixture-not-real','ANDROID_KEY_ALIAS':'fixture','ANDROID_KEY_PASSWORD':'fixture-not-real','HAPPYBOX_DATA_PROTECTION_TEST':'1','HAPPYBOX_SECURITY_PROBE_TEST':'0','GITHUB_REF':'refs/heads/ui/android-happybox-redesign','GITHUB_RUN_NUMBER':'161','RUNNER_TEMP':tmp,'GITHUB_ENV':str(output)}
            env.update(changes)
            capture=io.StringIO()
            with patch.dict(os.environ,env,clear=True),patch('subprocess.run',return_value=SimpleNamespace(returncode=0,stdout=certificate)),patch.object(verify_signed_apk,'PROBE_CERT_SHA256',anchor or hashlib.sha256(certificate).hexdigest()),contextlib.redirect_stdout(capture):
                runpy.run_path(str(ROOT/'scripts/prepare_ci_signing.py'),run_name='__main__')
            self.assertNotIn('fixture-not-real',capture.getvalue())
            self.assertIn('ANDROID_VERSION_CODE=100161',output.read_text())
    def test_fixed_certificate_checked_before_build(self):self.prepare()
    def test_wrong_fixed_certificate_stops_before_build(self):
        with self.assertRaisesRegex(SystemExit,'stopping before build'):self.prepare(anchor='0'*64)
    def test_missing_prior_apk_stops_before_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            env={'HAPPYBOX_DATA_PROTECTION_TEST':'1','GITHUB_REF':'refs/heads/ui/android-happybox-redesign','RUNNER_TEMP':tmp,'GITHUB_REPOSITORY':'offline/fixture'}
            cwd=Path.cwd()
            try:
                os.chdir(self.root)
                with patch.dict(os.environ,env,clear=True),patch('subprocess.run',return_value=SimpleNamespace(returncode=1)),self.assertRaisesRegex(SystemExit,'stop before build'):
                    protection.main()
            finally:os.chdir(cwd)
    def test_missing_signing_secret_stops_before_build(self):
        with self.assertRaises(SystemExit):self.prepare(ANDROID_KEY_PASSWORD='')
    def test_missing_all_signing_secrets_stops_before_build(self):
        with self.assertRaises(SystemExit):self.prepare(ANDROID_KEYSTORE_BASE64='',ANDROID_KEYSTORE_PASSWORD='',ANDROID_KEY_ALIAS='',ANDROID_KEY_PASSWORD='')
    def test_old_version_stops_before_build(self):
        with self.assertRaises(SystemExit):self.prepare(GITHUB_RUN_NUMBER='160')
    def test_main_branch_stops_before_build(self):
        with self.assertRaises(SystemExit):self.prepare(GITHUB_REF='refs/heads/main')
    def test_combined_probe_mode_stops_before_build(self):
        with self.assertRaises(SystemExit):self.prepare(HAPPYBOX_SECURITY_PROBE_TEST='1')

if __name__=='__main__':unittest.main()
