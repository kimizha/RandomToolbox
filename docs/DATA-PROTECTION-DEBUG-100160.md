# 开心盒 2.9 数据保护 Debug 测试包

本次获批构建的安装包基于 58dc8df 的保护功能，另增加专用构建与签名核验限制。只在 ui/android-happybox-redesign 开发，没有修改 main、腾讯云数据/集合/权限/函数、账号同步结构或 APK 更新配置，没有创建 Release。

## 下载

- [GitHub Actions 成功记录](https://github.com/kimizha/RandomToolbox/actions/runs/41619328457)
- [下载测试 APK ZIP](https://github.com/kimizha/RandomToolbox/actions/runs/41619328457/artifacts/13222716729)：附件 Happybox-data-protection-debug-apk，解压后安装 app-debug.apk。
- [APK 身份验证报告附件](https://github.com/kimizha/RandomToolbox/actions/runs/41619328457/artifacts/13222911602)
- [Android 原生测试报告附件](https://github.com/kimizha/RandomToolbox/actions/runs/41619328457/artifacts/13222243487)

GitHub Actions 附件通常需要先登录 GitHub。APK 为 Debug 数据保护测试版，不是正式发行版。

## 实际 APK 身份

| 项目 | 实际验证结果 |
| --- | --- |
| versionName | 2.9 |
| versionCode | 100160 |
| applicationId | com.randomtoolbox.app |
| debuggable | true |
| 源提交 | 79375362f47eec08df29704d2a9e41574ddf4149 |
| 固定证书 SHA-256 | 714524c73030e3d5010c849f52012af5adc7f36ecc2b0013ec6bff4c8324fa4b |
| APK SHA-256 | ad106a0bd365718b599d62e88fb413d1165584b8e0764938756683f8b94f39cc |
| 数据保护测试标记 | 包含 |
| 数据库探针入口 | 不包含 |
| 云端备份读写 | 暂停 |
| 本机 JSON 导出 | 包含 |

## 覆盖安装依据

Actions 构建前下载已交付的 100159 APK（artifact 13084658987），通过 apksigner 验证签名、aapt 读取实际身份，并核对其 SHA-256 为 7e7da6a16101a85b9dc417e555ddd4039282181a422655d23329fcbd5b11b591，与之前记录完全相同。固定签名 Secrets 对应的公开证书也先比对历史证书锚点，不输出签名密码或私钥。

构建完成后再次验证新旧 APK：相同包名、相同证书、100160 > 100159，报告 previous_apk.same_certificate=true、can_cover_install=true。只有全部检查通过后才上传 APK；不能获得旧 APK、签名不符、降版本、保护源码缺失等情况会停止构建或附件上传，没有临时签名兜底。

保留 https://appassets.androidplatform.net/assets/index.html 的 WebView 存储来源和 DOMStorage，不添加清 Cookie、清 LocalStorage 或删除数据库的操作。原 App 安装数据应通过覆盖安装保留；真实手机安装、登录会话和系统文件保存结果仍需按下述步骤验收，未将 CI 测试当作真机结果。

保留原安装直接更新，**不要卸载旧版，不要清除应用数据**。若系统仍拒绝更新，停止安装并保留旧版，记录错误信息核对；不要用卸载来解决。

## 手机导出步骤

1. 下载上述 ZIP，在手机文件管理器解压，点击 app-debug.apk，选择更新现有开心盒。系统如要求安装来源权限，仅给当前使用的浏览器或文件管理器授权。
2. 打开心盒，进入底部“我的”对应的设置页面，找到“本机数据备份”。无需先重新登录，也无需点击同步；该入口对游客可用。
3. 点击“导出本机 JSON 备份”，在系统保存界面选择手机的下载目录，保存 Happybox-local-backup-数字.json。
4. 等 App 提示“本机 JSON 备份已保存”，再到文件管理器确认文件存在且大小非零。取消或写入失败不会提示已保存，也不修改原数据。
5. 可用 JSON/文本查看器确认 format=happybox-local-backup、accountBackupSchema=2，storage 中保存了原始昵称/头像、工具配置、UID 缓存及本机棋牌记录。头像照片以数据字符串保存，不是额外图片附件。不要把包含私人资料的整份文件发到公开聊天。

同步界面应显示“云端初始化保护中”或“本机配置保留，归属待确认”，手动同步按钮不可用。修改配置、联网、回前台、定时器和退出登录都不会触发 account_backups 读写；不会自动创建集合或空备份。暂时不提供 JSON 自动恢复/导入，旧备份定位和后续恢复仍需独立审查。

## 构建改动与检查

- 工作流增加 data_protection_test 开关/提交标记，只构建 Debug；跳过诊断页面附件和两个 Release 发布步骤。正式发布脚本及 Gradle release 任务拒绝专用测试标记。
- prepare_ci_signing.py：数据保护构建必须使用四项固定签名 Secrets，必须位于 UI 分支、versionCode 高于 100159，不得与数据库探针模式混用。
- data_protection_build.py：构建前验证原包、签名、包名、版本递增、存储来源、同步暂停、备份入口和完整的 profile/sync/local-backup 源码打包一致性。
- verify_signed_apk.py：构建后验证实际 APK 身份和保护资源，再次严格比较旧 APK，生成公开核验报告。
- inject_auth.py / app/build.gradle / publish_ui_release.py：测试包标记与 Release 拦截。没有重写 58dc8df 的账号、资料、同步、备份或工具业务实现。
- 本地：22 项新构建保护检查、15 项发布限制、2 项固定证书检查、31 项同步回归、26 项实际浏览器备份检查通过，共 96 项；没有真实 CloudBase 调用。
- Actions：上述 CI 脚本检查、55 项 APK 更新策略检查、11 项 Android 原生单测、Debug 构建、打包资源核验、前后签名/覆盖身份核验全部通过。两个 Release 步骤均 skipped。

本次没有进行数据库读写验证，不表示新 Document API 已连通。仍未部署云函数、启用双设备踢出或改变旧客户端权限。
