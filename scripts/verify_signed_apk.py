"""Verify only public APK metadata/certificates; never print key material or passwords."""
import hashlib,json,os,re,shutil,subprocess,zipfile
from pathlib import Path

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
    return {'package_name':package[1],'version_code':int(package[2]),'version_name':package[3],'certificate_sha256':certs[0].lower(),'apk_sha256':hashlib.sha256(apk.read_bytes()).hexdigest()}

def main():
    sdk=Path(os.environ.get('ANDROID_HOME') or os.environ['ANDROID_SDK_ROOT'])
    tools=sdk/'build-tools/35.0.0'
    apk=Path('app/build/outputs/apk/debug/app-debug.apk')
    info=apk_info(apk,tools)
    expected_cert=hashlib.sha256(run(['keytool','-exportcert','-keystore',os.environ['ANDROID_KEYSTORE_FILE'],'-alias',os.environ['ANDROID_KEY_ALIAS'],'-storepass:env','ANDROID_KEYSTORE_PASSWORD'])).hexdigest()
    if info['certificate_sha256']!=expected_cert:raise SystemExit('APK certificate differs from configured stable signing key')
    if info['package_name']!='com.randomtoolbox.app':raise SystemExit('Unexpected Android package name')
    if info['version_code']!=int(os.environ['ANDROID_VERSION_CODE']):raise SystemExit('APK versionCode differs from CI versionCode')
    source=Path('app/build.gradle').read_text()
    if info['version_name']!=re.search(r"versionName '([^']+)'",source)[1]:raise SystemExit('APK versionName differs from source')
    info.update(source_commit=os.environ['GITHUB_SHA'],source_branch=os.environ['GITHUB_REF_NAME'],matches_configured_certificate=True)
    previous_id=os.environ.get('RT_PREVIOUS_APK_ARTIFACT_ID','')
    previous_tag=os.environ.get('RT_PREVIOUS_APK_RELEASE_TAG','')
    previous={'comparison':'unavailable'};old=None
    if previous_tag:
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
    info['previous_apk']=previous
    output=Path('release-output');output.mkdir(exist_ok=True)
    name=f"Happybox-v{info['version_name']}-code{info['version_code']}.apk"
    shutil.copyfile(apk,output/name);info['apk_filename']=name
    (output/'verification.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n')
    (output/'SHA256SUMS').write_text(info['apk_sha256']+'  '+name+'\n')
    print('RT_APK_VERIFICATION='+json.dumps(info,ensure_ascii=False))

if __name__=='__main__':main()
