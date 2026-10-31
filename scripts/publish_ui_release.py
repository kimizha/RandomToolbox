"""Publish a verified UI-branch prerelease without touching main or existing tags."""
import json,os,subprocess
from pathlib import Path

def gh(args):
    r=subprocess.run(['gh',*args],capture_output=True,text=True)
    if r.returncode:raise SystemExit('GitHub release operation failed; existing releases were not overwritten')
    return r.stdout

def main():
    if os.environ.get('GITHUB_REF')!='refs/heads/ui/android-happybox-redesign':raise SystemExit('Release requires the UI development branch')
    if os.environ.get('RT_STABLE_SIGNING')!='true':raise SystemExit('Stable signing must be configured')
    output=Path('release-output');report=json.loads((output/'verification.json').read_text())
    if report['source_commit']!=os.environ['GITHUB_SHA'] or not report['matches_configured_certificate']:raise SystemExit('Verification/source mismatch')
    tag=f"ui-v{report['version_name']}-code{report['version_code']}"
    exists=subprocess.run(['gh','release','view',tag],capture_output=True)
    if exists.returncode==0:raise SystemExit('Release tag already exists; refusing to overwrite it')
    old=report['previous_apk']
    if old.get('comparison')=='verified' and not old['same_certificate']:
        migration='**与此前提供的旧 APK 签名不同，无法直接覆盖安装。不要直接卸载旧版。**\n\n请先在“账号同步”中确认上传成功，并在保留旧安装的条件下确认云端配置和独立数据备份可恢复，再制定首次迁移步骤。当前尚未确认真实账号的云端备份状态。'
    elif old.get('comparison')=='verified':
        migration='与此前提供的旧 APK 签名一致，包名一致且 versionCode 已递增。覆盖安装仍需在手机上验证；请先确认账号同步及数据备份情况。'
    else:
        migration='未能取得此前 APK 的证书，不能确认能否覆盖安装。请保留旧版，先核对证书并确认账号云端同步和数据备份，不要为安装而直接卸载。'
    fingerprint=':'.join(report['certificate_sha256'][i:i+2] for i in range(0,64,2)).upper()
    notes=f"""开心盒 2.7 · UI 分支开发测试版，固定签名 APK。\n\n转盘配置按钮移至标题右侧，示例明确分行；修复登录恢复、离线缓存、账号隔离与同步状态。\n\n- 包名：`{report['package_name']}`\n- versionName：`{report['version_name']}`\n- versionCode：`{report['version_code']}`\n- 源提交：`{report['source_commit']}`（`ui/android-happybox-redesign`）\n- 签名证书 SHA-256：`{fingerprint}`\n- APK SHA-256：`{report['apk_sha256']}`\n\n{migration}\n\n137 项浏览器检查与 21 组模拟同步场景通过；真实账号跨设备恢复、手机覆盖安装尚未验收。保持同一固定签名才能支持后续版本覆盖升级。\n\n构建记录：https://github.com/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}\n"""
    body=Path(os.environ['RUNNER_TEMP'])/'happybox-release-notes.md';body.write_text(notes)
    gh(['release','create',tag,str(output/report['apk_filename']),str(output/'verification.json'),str(output/'SHA256SUMS'),'--target',report['source_commit'],'--title',f"开心盒 v{report['version_name']} · UI 测试版 ({report['version_code']})",'--notes-file',str(body),'--prerelease','--latest=false'])
    release=json.loads(gh(['api',f"repos/{os.environ['GITHUB_REPOSITORY']}/releases/tags/{tag}"]))
    info={**report,'tag':tag,'release_url':release['html_url'],'download_url':next(a['browser_download_url'] for a in release['assets'] if a['name']==report['apk_filename'])}
    (output/'release-info.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n')
    print('RT_RELEASE_INFO='+json.dumps(info,ensure_ascii=False))
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:f.write(notes+'\n\n下载：'+info['download_url']+'\n')

if __name__=='__main__':main()
