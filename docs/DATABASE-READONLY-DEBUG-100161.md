# 开心盒 2.9 Debug 100161 · 手机一键只读验收

## 下载与源码

- [成功的 GitHub Actions 构建](https://github.com/kimizha/RandomToolbox/actions/runs/41811676039)
- [下载 APK ZIP](https://github.com/kimizha/RandomToolbox/actions/runs/41811676039/artifacts/13312193708)：附件 Happybox-database-readonly-debug-apk，解压得到 app-debug.apk。
- [下载公开 APK 签名及覆盖核验报告](https://github.com/kimizha/RandomToolbox/actions/runs/41811676039/artifacts/13312218755)
- [Android 原生单测报告](https://github.com/kimizha/RandomToolbox/actions/runs/41811676039/artifacts/13311994536)
- APK 源提交：3fe2dcbe47b00cb30b71be922816ab36849fbe13。
- 开发分支：ui/android-happybox-redesign，基于已安装的 100160 数据保护版；没有修改 main。

Actions 附件需登录 GitHub 下载。此包是临时 Debug 测试版，没有创建或更新 GitHub Release。

## APK 实际核验

| 项目 | 结果 |
| --- | --- |
| versionName | 2.9 |
| versionCode | 100161 |
| applicationId | com.randomtoolbox.app |
| Debug | 是 |
| 固定证书 SHA-256 | 714524c73030e3d5010c849f52012af5adc7f36ecc2b0013ec6bff4c8324fa4b |
| APK SHA-256 | 84883b29f6e47a4e76df7fc4e01902a2dcd95fbf4ce404ce16b4014fa849ce03 |
| 临时只读核验入口 | 包含 |
| 云端同步暂停 | 保持 |
| 本机 JSON 备份 | 保留 |
| 与 100160 相同证书 | 是 |
| 与 100160 相同包名、版本递增 | 是 |

构建前下载已交付 100160（artifact 13222716729），核对其实际签名、包名、版本和 APK SHA-256 ad106a0bd365718b599d62e88fb413d1165584b8e0764938756683f8b94f39cc。构建后再次用 apksigner/aapt 核对新旧两包，previous_apk.same_certificate 和 can_cover_install 均为 true，才上传 APK。

保持原 WebView 存储来源、DOMStorage 和应用包名，没有清 Cookie、LocalStorage 或用户数据的代码。直接覆盖安装，不卸载旧版、不清除数据。真实手机上的安装及会话恢复结果仍由安装后确认；若系统拒绝更新，保留旧版并反馈提示，不能靠卸载解决。

报告中的 contains_data_protection_test=false 仅表示没有使用 100160 的“纯数据保护测试包”模式标记；本包使用只读核验测试标记。cloud_sync_paused=true、local_json_export=true，并已对比打包的同步/资料/备份源码，保护功能没有移除。

## 手机真实验收

1. 下载并解压 ZIP，使用 app-debug.apk 更新原开心盒。
2. 打开“我的”，向下找到“开发测试”，点击“数据库连接测试（只读）”。已有有效会话直接复用，不需要重新输入账号、UID 或任何密钥。
3. 等待身份、普通读取、事务读取三个分区结果。界面超时不会放任重叠请求；缺失函数、身份拒绝或修订不匹配会停止核验，不自动修复线上资源。
4. 点击“复制诊断摘要”，把摘要反馈即可。无需提供 UID、Token、完整响应或本机备份文件。

空集合预期：普通读取 readVerified=true，DOCUMENT_ABSENT、documentFound=false；事务 transactionReadVerified=true、READ_PREFLIGHT_COMPLETE、phase=COMPLETE，同样 DOCUMENT_ABSENT；综合 BOTH_READS_VERIFIED。不存在本人文档不需要创建记录。

普通成功、事务失败会显示 TRANSACTION_READ_FAILED；普通失败、事务成功显示 ORDINARY_READ_FAILED；两者均未核实或证据矛盾显示 BOTH_UNVERIFIED。阶段、诊断码及服务端原 comparisonCode 仍分别保留。修订不等于 readonly-comparison-v3 显示 PROBE_REVISION_MISMATCH，不以身份成功或版本匹配替代读取成功。

本轮没有真实 CloudBase 会话可用于正向调用，也没有读取线上 $LATEST 源码的管理连接。页面和摘要保留“线上源码摘要尚未远程核实”。不能把客户端模拟、修订标记或 APK 构建通过当作真实数据库验收；真实结果以手机点击后返回为准。

## 修改文件清单

1. scripts/probe-context.js：新增实际 SDK/认证实例适配器，调用前后核对会话与账号。
2. scripts/dev-security-probe.js：原测试入口改为一键核验、分区结果、脱敏复制和并发/超时保护。
3. scripts/dev-security-probe.css：开发测试区域样式、加载动画、深色与小屏适配。
4. scripts/inject_auth.py：仅测试模式在实际 SDK 初始化位置捕获上下文并注入入口；原认证过程保持。
5. scripts/data_protection_build.py：两类临时包均核对数据保护资源，基准更新到 100160。
6. scripts/prepare_ci_signing.py：固定证书、UI 分支和 versionCode >100160 的构建前限制。
7. scripts/verify_signed_apk.py：实际打包源码、入口、签名及与 100160 覆盖条件核验。
8. .github/workflows/build-apk.yml：离线浏览器验收、构建前保护核验及专用附件名称。
9. scripts/check_dev_security_probe.py：完整注入页面的 55 项离线集成测试。
10. scripts/check_data_protection_build.py：27 项源码打包、签名基准和安全构建检查。
11. scripts/check_probe_signing.py：固定证书测试更新到当前版本边界。
12. scripts/check_release.py：测试包无法凭伪造报告进入 Release 的回归检查。
13. docs/DATABASE-READONLY-ENTRY.md：设计、安全边界与后续完整删除方式。
14. docs/DEV-PROBE-ENTRY.md：指向新入口，保留旧文档作历史记录。
15. 本交付文档：实际下载与手机操作记录。

## 检查结果与线上变更

- 本地 156 项通过：55 项入口集成、27 项构建保护、15 项发布限制、2 项固定签名、31 项同步回归、26 项本机备份。
- Actions：离线入口集成、保护/同步/只读探针模拟、55 项 APK 更新策略、11 项 Android 原生单测、Debug 编译、完整资产及新旧 APK 签名/身份核验全部通过。
- 两个 Release 发布步骤均 skipped。没有测试失败或临时签名兜底。
- scripts/sync.js、profile.js、local-backup.js、MainActivity.java、AndroidManifest.xml、cloudfunctions、updates 未改动；本地 V3 六源文件与原部署 ZIP 仍一致。
- **未修改腾讯云线上资源**：没有部署函数、修改环境变量或权限、创建/修改业务文档、导入备份、恢复同步或启用设备踢出。自动化测试全部使用隔离 SDK，未发送真实 CloudBase 请求。

只读验收不证明并发写入或双设备限制已经实现。这些仍需后续单独获批验证。
