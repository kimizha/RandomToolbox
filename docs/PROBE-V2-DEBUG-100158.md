# 新版只读探针适配 Debug APK 100158

本次仅在 ui/android-happybox-redesign 适配测试入口并构建 Debug，未修改 CloudBase 函数、权限、认证规则、同步数据结构、设备功能或正式版本。真实手机上的新版事务读取仍待用户操作验证。

## 构建交付

- 源提交：b62d5935e515ea1c2ff89fc01d3713c4fc266c05。
- [Actions 构建记录](https://github.com/kimizha/RandomToolbox/actions/runs/41305705073)：成功。
- [下载 Debug APK 附件](https://github.com/kimizha/RandomToolbox/actions/runs/41305705073/artifacts/13083342774)：Happybox-security-probe-debug-apk。需登录 GitHub；ZIP 内为 app-debug.apk。
- versionName：2.9；versionCode：100158，高于现有 100157；包名：com.randomtoolbox.app。
- debuggable=true，contains_security_probe=true，HAPPYBOX_SECURITY_PROBE_TEST=1。
- 固定证书 SHA-256：714524c73030e3d5010c849f52012af5adc7f36ecc2b0013ec6bff4c8324fa4b。
- APK SHA-256：8592812a89c7d8609c00cf1f9ac28cf5cd589ad042f951f962948cc8f80f5e35。
- 构建前导出公钥证书比对 100157 的固定指纹，构建后再检查 APK 实际证书；不一致会中止、不上传 APK、不使用临时签名。
- 两个 Release 发布步骤均跳过，没有创建 GitHub Release。没有修改 main、version.json 或正式构建默认模式。

## 修改文件

| 文件 | 修改 |
| --- | --- |
| scripts/dev-security-probe.js | 删除旧提交号确认文案；安全展示 v2 字段、一致性检查、旧版/字段缺失与矛盾响应拒绝成功 |
| scripts/security_probe_manifest.py | 验证本地 ZIP 中五个源文件与仓库一致，计算真实包 SHA-256、文件 SHA-256 并读取修订标记 |
| scripts/inject_auth.py | 仅显式测试模式注入上述摘要与入口；默认不包含测试代码 |
| scripts/prepare_ci_signing.py | 在构建前校验证书指纹，不一致立即停止 |
| scripts/verify_signed_apk.py | 构建后固定证书锚点复核，测试 code 必须高于 100157 |
| scripts/check_dev_security_probe.py | 29 项入口、错误脱敏、版本兼容、摘要与隔离检查 |
| scripts/check_release.py | 11 项 APK/发布保护检查，含旧证书不一致拒绝 |
| scripts/check_probe_signing.py | 2 项构建前证书匹配/不匹配模拟 |
| .github/workflows/build-apk.yml | 增加上述签名与事务检查，沿用既有专用 Debug 开关与发布拦截 |

本页为额外构建记录，不改变 APK 源提交。

## 本地摘要与线上验证的边界

测试入口的“查看本地部署包与源码核对信息”显示：

- 修订标记 readonly-tx-null-v2。
- 实际 v2 ZIP SHA-256：aefc4a54a767ed17bda4cdabc502fc614a8682d7bd8fdf5c4a8e7163183a7370。
- index.js、probe.cjs、transaction-read.cjs、package.json、package-lock.json 的实际文件摘要。
- 构建时这五个文件与本地 ZIP 逐字节匹配。任一不匹配，测试注入中止。

Git 提交号不是包摘要；文件名也不能证明部署成功。确认框默认不勾选，不保存勾选状态。默认文字为“线上版本尚未核实”。收到匹配修订后仅显示“服务端修订标记匹配；线上源码摘要未由客户端远程核实”，不自动给出线上源码通过结论。

## 手机安装与真实会话核验

1. 下载本页指定的新附件并解压，点击 app-debug.apk **直接覆盖安装**。不卸载、不清数据；如安装失败先保留旧包并反馈系统提示。
2. 确认原收藏、转盘和资料仍在，使用原有登录会话或原登录界面登录获准的测试账号。不向探针填写 UID、密码或 token。
3. 设置页向下找到“开发测试 · 只读安全核验”，展开本地摘要信息。按当前线上代码的实际文件核对；不能只看控制台显示成功或出现 helper 文件。
4. 核对后自己勾选人工确认，再点击“使用当前真实会话核验”。不自动勾选、不自动调用、不轮询。
5. 页面显示：身份状态、当前 UID 是否与服务端可信身份/环境一致、修订标记、事务读取状态、phase、diagnosticCode、stageCode、结果代码、是否存在本人文档。
6. 成功应为身份确认、UID 一致、修订匹配、phase=COMPLETE、READ_PREFLIGHT_COMPLETE。DOCUMENT_PRESENT 表示本人文档存在；DOCUMENT_ABSENT 是正常空结果，不需要人为创建记录。成功时 stageCode 显示不适用。
7. 失败反馈这几个安全状态即可。例如 phase=COMMIT、stageCode=COMMIT_PERMISSION_DENIED 会明确显示未通过；不能据失败判断文档不存在。旧标记、缺字段、未知值或矛盾响应都不会显示读取成功。
8. 若看到部署不匹配或调用异常，先核对源码并反馈，不为测试修改权限、重新部署或伪造身份。重新认证证明、并发写入、底层令牌撤销仍为未核实。

入口复用真实 SDK getSession 和固定 callFunction(name=happyboxSecurityProbe,data={})，不会更改登录状态或提交 UID。用户切换后丢弃旧结果；返回字段以固定枚举过滤，不输出未知原文、token、密钥、备份或堆栈。当前 UID 仅显示是否一致，不展示其他账号的 UID。

现有正常账号同步保留，使用者原有配置修改仍可能按原同步逻辑上传；只读探针本身不写数据库、不上传随机历史。

## 测试结果与限制

通过：29 项入口与摘要检查、21 项探针模拟、20 项事务场景、22 项同步模拟、210 项既有 UI 回归、11 项发布/身份保护检查、2 项构建前证书检查。CI 的原生单元测试、55 项 APK 更新策略及签名/包名/版本/探针模式核验通过。没有已知失败检查；没有把模拟结果当真实腾讯云验收。

本次没有构建 release 变体。隔离依据是默认不注入、原生 debug 门槛、release 资产拒绝、验证及发布脚本拒绝探针包；正式构建默认模式和原有流程保留。
