"""Verify only public APK metadata/certificates; never print key material or passwords."""
import hashlib,json,os,re,shutil,subprocess,zipfile
from pathlib import Path

PROBE_CERT_SHA256='714524c73030e3d5010c849f52012af5adc7f36ecc2b0013ec6bff4c8324fa4b'

def run(args,**kwargs):
    result=subprocess.run(args,capture_output=True,**kwargs)
    if result.returncode:raise SystemExit('Verification command failed: '+Path(args[0]).name+' (credentials and command output omitted)')
    return result.stdout

def apk_info(apk,tools):
    output=run([str(tools/'apksigner'),'verify','--verbose','--print-certs',str(apk)],text=True)
    certs=re.findall(r'Signer #\d+ certificate SHA-256 digest:\s*([0-9a-fA-F]{64})',output)
    if len(certs)!=1:raise SystemExit('APK must have exactly one verified signer')
    badging=run([str(tools/'aapt'),'dump','badging',str(apk)],text=True)
    package=re.search(r"^package: name='([^']+)' versionCode='(\d+)' versionName='([^']+)'",badging,re.M)
    if not package:raise SystemExit('APK package/version metadata unavailable')
    return {'package_name':package[1],'version_code':int(package[2]),'version_name':package[3],'debuggable':bool(re.search(r'^application-debuggable(?:\s|$)',badging,re.M)),'certificate_sha256':certs[0].lower(),'apk_sha256':hashlib.sha256(apk.read_bytes()).hexdigest()}

def main():
    sdk=Path(os.environ.get('ANDROID_HOME') or os.environ['ANDROID_SDK_ROOT'])
    tools=sdk/'build-tools/35.0.0'
    apk=Path('app/build/outputs/apk/debug/app-debug.apk')
    info=apk_info(apk,tools)
    with zipfile.ZipFile(apk) as archive:
        html=archive.read('assets/index.html').decode('utf-8')
        info['contains_security_probe']='HAPPYBOX_SECURITY_PROBE_TEST_ONLY' in html
        info['contains_data_protection_test']='HAPPYBOX_DATA_PROTECTION_TEST_ONLY' in html
    protection=os.environ.get('HAPPYBOX_DATA_PROTECTION_TEST')=='1'
    if info['contains_data_protection_test']!=protection:raise SystemExit('APK protection mode differs from requested build')
    if protection:
        from data_protection_build import validate_source,validate_assets
        validate_source(Path.cwd());validate_assets(html,Path.cwd())
        if not info['debuggable'] or info['version_code']<=100159 or info['certificate_sha256']!=PROBE_CERT_SHA256:
            raise SystemExit('Protection APK identity cannot cover delivered Debug APK 100159')
        info.update(data_protection_test=True,cloud_sync_paused=True,local_json_export=True)
    expected_probe=os.environ.get('HAPPYBOX_SECURITY_PROBE_TEST')=='1'
    if info['contains_security_probe']!=expected_probe:raise SystemExit('APK probe inclusion differs from explicit build mode')
    if expected_probe and (not info['debuggable'] or info['version_code']<=100158):raise SystemExit('Probe requires a Debug APK newer than 100158')
    expected_cert=hashlib.sha256(run(['keytool','-exportcert','-keystore',os.environ['ANDROID_KEYSTORE_FILE'],'-alias',os.environ['ANDROID_KEY_ALIAS'],'-storepass:env','ANDROID_KEYSTORE_PASSWORD'])).hexdigest()
    if expected_probe and info['certificate_sha256']!=PROBE_CERT_SHA256:raise SystemExit('Probe certificate differs from the previously delivered Debug APK; stop without fallback')
    if info['certificate_sha256']!=expected_cert:raise SystemExit('APK certificate differs from configured stable signing key')
    if info['package_name']!='com.randomtoolbox.app':raise SystemExit('Unexpected Android package name')
    if info['version_code']!=int(os.environ['ANDROID_VERSION_CODE']):raise SystemExit('APK versionCode differs from CI versionCode')
    source=Path('app/build.gradle').read_text()
    if info['version_name']!=re.search(r"versionName '([^']+)'",source)[1]:raise SystemExit('APK versionName differs from source')
    info.update(source_commit=os.environ['GITHUB_SHA'],source_branch=os.environ['GITHUB_REF_NAME'],matches_configured_certificate=True)
    previous_id=os.environ.get('RT_PREVIOUS_APK_ARTIFACT_ID','')
    previous_tag=os.environ.get('RT_PREVIOUS_APK_RELEASE_TAG','')
    previous={'comparison':'unavailable'};old=None
    if protection:
        path=os.environ.get('RT_DATA_PROTECTION_PRIOR_APK')
        if not path or not Path(path).is_file():raise SystemExit('Verified previous APK is required; stop distribution')
        old=Path(path);previous['artifact_id']='13084658987'
    if old is None and previous_tag:
        folder=Path(os.environ['RUNNER_TEMP'])/'previous-release';folder.mkdir(exist_ok=True)
        result=subprocess.run(['gh','release','download',previous_tag,'--repo',os.environ['GITHUB_REPOSITORY'],'--pattern','*.apk','--dir',str(folder)],capture_output=True)
        files=list(folder.glob('*.apk'))
        if result.returncode==0 and len(files)==1 and files[0].stat().st_size<128*1024*1024:
            old=files[0];previous['release_tag']=previous_tag
    if old is None and previous_id:
        archive=Path(os.environ['RUNNER_TEMP'])/'previous-apk.zip'
        with archive.open('wb') as out:
            fetched=subprocess.run(['gh','api',f"repos/{os.environ['GITHUB_REPOSITORY']}/actions/artifacts/{previous_id}/zip"],stdout=out,stderr=subprocess.PIPE)
        if fetched.returncode==0:
            with zipfile.ZipFile(archive) as z:
                items=[x for x in z.infolist() if x.filename.endswith('.apk') and x.file_size<128*1024*1024]
                if len(items)!=1:raise SystemExit('Prior APK archive does not contain exactly one bounded APK')
                old=Path(os.environ['RUNNER_TEMP'])/'previous-app.apk';old.write_bytes(z.read(items[0]))
            previous['artifact_id']=previous_id
    if old is not None:
        previous.update(apk_info(old,tools));previous['comparison']='verified'
        if info['package_name']!=previous['package_name']:raise SystemExit('New and prior APK package names differ')
        if info['version_code']<=previous['version_code']:raise SystemExit('New APK versionCode must exceed previously delivered APK')
        previous['same_certificate']=info['certificate_sha256']==previous['certificate_sha256']
        previous['can_cover_install']=previous['same_certificate']
        if protection:
            from data_protection_build import validate_previous
            validate_previous(previous,info['version_code'],expected_cert)
            if not previous['can_cover_install']:raise SystemExit('Protection APK cannot cover old version; stop distribution')
    info['previous_apk']=previous
    output=Path('release-output');output.mkdir(exist_ok=True)
    name=f"Happybox-v{info['version_name']}-code{info['version_code']}.apk"
    shutil.copyfile(apk,output/name);info['apk_filename']=name
    (output/'verification.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n')
    (output/'SHA256SUMS').write_text(info['apk_sha256']+'  '+name+'\n')
    print('RT_APK_VERIFICATION='+json.dumps(info,ensure_ascii=False))

if __name__=='__main__':main()
