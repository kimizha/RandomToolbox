"""Create a private signing kit outside the repository; never print credentials."""
import base64, os, secrets, subprocess, sys
from pathlib import Path
out=Path(sys.argv[1] if len(sys.argv)>1 else '/workspace/Happybox-private-signing').resolve()
repo=Path(__file__).resolve().parents[1]
if out==repo or repo in out.parents:raise SystemExit('Signing material must be stored outside the repository')
out.mkdir(parents=True,exist_ok=True);out.chmod(0o700)
keystore=out/'happybox-upload.p12'
if keystore.exists():raise SystemExit('Existing signing kit preserved; will not replace its key')
password=secrets.token_urlsafe(40);alias='happybox'
env={**os.environ,'RT_SIGN_PASSWORD':password}
subprocess.run(['keytool','-genkeypair','-storetype','PKCS12','-keystore',str(keystore),'-alias',alias,'-keyalg','RSA','-keysize','3072','-validity','10000','-dname','CN=Happybox Android, O=Happybox','-storepass:env','RT_SIGN_PASSWORD','-keypass:env','RT_SIGN_PASSWORD'],env=env,check=True,capture_output=True)
files={'ANDROID_KEYSTORE_BASE64.txt':base64.b64encode(keystore.read_bytes()).decode(),'ANDROID_KEYSTORE_PASSWORD.txt':password,'ANDROID_KEY_PASSWORD.txt':password,'ANDROID_KEY_ALIAS.txt':alias}
for name,value in files.items():
 p=out/name;p.write_text(value,encoding='utf-8');p.chmod(0o600)
keystore.chmod(0o600)
(out/'README.txt').write_text('固定签名私密资料，请妥善备份，勿提交到 Git 仓库或公开分享。\n\n在 GitHub 仓库 Settings > Secrets and variables > Actions 中创建四个 Repository secrets，名称为对应 txt 文件名去掉 .txt，值为文件全部内容。\n\n也可以在有仓库 Secrets 写权限的本机执行：\npython3 scripts/install_android_signing_secrets.py '+str(out)+' kimizha/RandomToolbox\n\n添加完后重新运行 UI 分支构建。同一密钥必须用于此后所有版本。旧临时签名 APK 的私钥不能从 APK 中恢复，因此首次切换固定签名仍无法直接覆盖旧临时签名版本；先确认账号配置已同步，再考虑卸载旧包。\n',encoding='utf-8')
print('Private signing kit prepared at '+str(out)+' (credentials omitted)')
