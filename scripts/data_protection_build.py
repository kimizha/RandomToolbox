"""Fail-closed protection Debug preflight. Reads only public APK metadata; no CloudBase calls."""
import hashlib, json, os, re, subprocess, zipfile
from pathlib import Path
from verify_signed_apk import apk_info, PROBE_CERT_SHA256, run

PRIOR_ARTIFACT_ID='13222716729'
PRIOR_CODE=100160
PRIOR_APK_SHA256='ad106a0bd365718b599d62e88fb413d1165584b8e0764938756683f8b94f39cc'
MARKER='HAPPYBOX_DATA_PROTECTION_TEST_ONLY'

def validate_source(root):
    root=Path(root)
    gradle=(root/'app/build.gradle').read_text()
    if re.findall(r"applicationId\s+'([^']+)'",gradle)!=['com.randomtoolbox.app'] or 'applicationIdSuffix' in gradle:
        raise SystemExit('Protection package identity must stay unchanged')
    native=(root/'app/src/main/java/com/randomtoolbox/app/MainActivity.java').read_text()
    if 'HOME_URL = "https://appassets.androidplatform.net/assets/index.html"' not in native or 's.setDomStorageEnabled(true)' not in native:
        raise SystemExit('Protection build must preserve the WebView storage origin')
    if any(term in native for term in ['clearCache(', 'removeAllCookies(', 'deleteDatabase(', 'WebStorage.getInstance().deleteAllData(']):
        raise SystemExit('Unexpected WebView data clearing operation')
    if 'const RT_SYNC_CLOUD_PAUSED=true;' not in (root/'scripts/sync.js').read_text():
        raise SystemExit('Cloud synchronization must remain paused')
    if 'Intent.ACTION_CREATE_DOCUMENT' not in native or 'void exportLocalBackup(' not in native:
        raise SystemExit('Native local JSON export is missing')

def validate_assets(html,root,probe=False):
    root=Path(root)
    for name in ['sync.js','profile.js','local-backup.js']:
        if html.count((root/'scripts'/name).read_text())!=1:
            raise SystemExit('Bundled account/protection source mismatch: '+name)
    if html.count('const RT_SYNC_CLOUD_PAUSED=true;')!=1 or html.count('function rtSyncTick(')!=1:
        raise SystemExit('Unexpected synchronization guard or duplicate implementation')
    if probe:
        from security_probe_manifest import create_manifest
        manifest=create_manifest(root)
        if 'HAPPYBOX_SECURITY_PROBE_TEST_ONLY' not in html or MARKER in html:
            raise SystemExit('Read-only probe build mode mismatch')
        for name in ['probe-context.js','dev-security-probe.js','dev-security-probe.css']:
            if html.count((root/'scripts'/name).read_text())!=1:raise SystemExit('Probe asset source mismatch: '+name)
        if manifest['packageSha256'] not in html or 'window.hbAttachProbeContext({app,auth:rtAuth,' not in html:
            raise SystemExit('Reviewed probe evidence or actual SDK attachment missing')
    elif MARKER not in html or 'HAPPYBOX_SECURITY_PROBE_TEST_ONLY' in html:
        raise SystemExit('Protection Debug assets must not include a database probe')
    if 'data-rt-backup-export' not in html or '导出本机 JSON 备份' not in html:
        raise SystemExit('Local backup entry is missing')

def validate_previous(previous,next_code,configured_cert):
    if previous['package_name']!='com.randomtoolbox.app' or previous['version_code']!=PRIOR_CODE:
        raise SystemExit('Previous delivered APK identity could not be established')
    if previous['apk_sha256']!=PRIOR_APK_SHA256:
        raise SystemExit('Previous APK differs from the recorded APK 100160 digest')
    if previous['certificate_sha256']!=PROBE_CERT_SHA256 or configured_cert!=previous['certificate_sha256']:
        raise SystemExit('Fixed certificate differs from delivered APK 100160; no fallback')
    if next_code<=previous['version_code']:
        raise SystemExit('New versionCode cannot cover the delivered APK')

def main():
    probe=os.environ.get('HAPPYBOX_SECURITY_PROBE_TEST')=='1'
    if not(probe or os.environ.get('HAPPYBOX_DATA_PROTECTION_TEST')=='1') or os.environ.get('GITHUB_REF')!='refs/heads/ui/android-happybox-redesign':
        raise SystemExit('Explicit UI-branch protection test build required')
    validate_source(Path.cwd())
    validate_assets(Path('app/src/main/assets/index.html').read_text(),Path.cwd(),probe=probe)
    archive=Path(os.environ['RUNNER_TEMP'])/'protection-prior-100160.zip'
    with archive.open('wb') as output:
        fetched=subprocess.run(['gh','api',f"repos/{os.environ['GITHUB_REPOSITORY']}/actions/artifacts/{PRIOR_ARTIFACT_ID}/zip"],stdout=output,stderr=subprocess.PIPE)
    if fetched.returncode:raise SystemExit('Cannot retrieve prior APK; stop before build, do not uninstall')
    prior_apk=Path(os.environ['RUNNER_TEMP'])/'protection-prior-100160.apk'
    try:
        with zipfile.ZipFile(archive) as z:
            entries=[x for x in z.infolist() if x.filename.endswith('.apk') and x.file_size<128*1024*1024]
            if len(entries)!=1:raise SystemExit('Previous APK archive is invalid')
            prior_apk.write_bytes(z.read(entries[0]))
    except zipfile.BadZipFile:raise SystemExit('Previous APK download is not a valid ZIP')
    sdk=Path(os.environ.get('ANDROID_HOME') or os.environ['ANDROID_SDK_ROOT'])
    previous=apk_info(prior_apk,sdk/'build-tools/35.0.0')
    certificate=run(['keytool','-exportcert','-keystore',os.environ['ANDROID_KEYSTORE_FILE'],'-alias',os.environ['ANDROID_KEY_ALIAS'],'-storepass:env','ANDROID_KEYSTORE_PASSWORD'])
    validate_previous(previous,int(os.environ['ANDROID_VERSION_CODE']),hashlib.sha256(certificate).hexdigest())
    with open(os.environ['GITHUB_ENV'],'a') as output:output.write('RT_DATA_PROTECTION_PRIOR_APK='+str(prior_apk)+'\n')
    print('Protection preflight passed: '+json.dumps({'previous_apk':previous,'next_version_code':int(os.environ['ANDROID_VERSION_CODE']),'cloud_sync_paused':True,'local_export_included':True}))

if __name__=='__main__':main()
