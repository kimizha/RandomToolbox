# 专用 Debug 探针测试包（非正式版本）

用户确认线上四个探针源文件与 813c2f5 一致后，批准本次专用测试构建。没有修改或部署云函数，没有变更生产数据库规则、账号资料或设备会话功能。

## 构建与下载

- 源提交：522a3ebdf3e7d20b94ea4ca31d8da3d645b855ff，ui/android-happybox-redesign。
- [GitHub Actions 记录](https://github.com/kimizha/RandomToolbox/actions/runs/41296424378)：成功。
- [下载测试 APK 附件](https://github.com/kimizha/RandomToolbox/actions/runs/41296424378/artifacts/13079960508)：Happybox-security-probe-debug-apk。需登录有仓库访问权限的 GitHub 账号。
- ZIP 解压后安装 app-debug.apk；这是测试附件，不是 GitHub Release。
- versionName：2.9；实际 versionCode：100157（高于现有 100156）；包名：com.randomtoolbox.app。
- aapt 确认 debuggable=true；实际 APK 资产确认 contains_security_probe=true；工作流 HAPPYBOX_SECURITY_PROBE_TEST=1。
- 证书 SHA-256：714524c73030e3d5010c849f52012af5adc7f36ecc2b0013ec6bff4c8324fa4b，与原固定证书及被比较的旧固定签名包一致。
- APK SHA-256：56f65f6983bf0d14ab93f1ab220d3e76e1dd5cd30d6e75c52becad0d5a5fee61。

两个 Release 发布步骤均跳过。没有修改 version.json，强制更新仍关闭、下载地址仍为空。版本名保持 2.9，不将此探针测试包标记为已完成的 v3.0。

## 手机安装与核验

1. 保留现有开心盒安装。下载 ZIP、解压并点击 app-debug.apk，按系统提示允许所用浏览器/文件管理器安装，再直接覆盖升级；不要卸载或清除 App 数据。
2. 打开 App，检查原工具、收藏、转盘与个人资料。有效原登录会话应按原机制恢复；若会话真实失效，使用现有登录流程登录原测试账号。
3. 进入设置，向下找到“开发测试 · 只读安全核验”。确认已完成线上源码核对，勾选确认框。
4. 点击“使用当前真实会话核验”，等待一次调用完成。没有额外 UID、密码或 token 输入框，不自动轮询。
5. identityVerified=true 且页面本人 UID 与 CloudBase 用户管理中的本人 UID 一致，说明本次真实身份核验成功。对外反馈可遮盖 UID。
6. transactionReadVerified=true 且 READ_PREFLIGHT_COMPLETE 表示本次只读事务有效返回；不等于备份一定存在，也不证明并发写入或设备限制安全。
7. 若 PROBE_NOT_AUTHORIZED，先检查当前真实测试 UID 是否在服务端 HAPPYBOX_PROBE_ALLOWED_UIDS 中；不放宽数据库权限，不在前端伪造身份。
8. 若读取尚未核实，反馈页面状态代码即可，不提供 token、密钥或备份正文。重新认证证明、并发写入和底层令牌按设备撤销继续属于未验证事项。

现有账号同步仍运行，用户原有设置修改可能通过原同步上传；探针本身仅调用已部署只读函数，不新增同步或写入操作。

## 测试与正式版本隔离

本地 17 项入口检查与 10 项 APK 验证/发布保护检查通过；CI 通过 19 项探针模拟、22 项账号同步模拟、55 项 APK 更新策略检查、原生单元测试及 Debug APK 构建与签名核验。模拟与编译不代替本次真机 CloudBase 调用。

本次构建通过一次性提交标记选择测试模式；以后普通构建默认 HAPPYBOX_SECURITY_PROBE_TEST=0。手动 Run workflow 可显式选择 security_probe；该选项仅 UI 分支有效，且测试模式禁止 Release 发布。默认资产不注入入口；release 任务若发现测试标记会中止，APK 验证也拒绝构建模式与入口不匹配。现有发布脚本再次检查实际 APK 防止测试包被发布。

用户未批准正式版发布，没有构建 release 变体，也没有合并 main。将来正式构建必须使用干净源码并关闭测试模式，不复用测试注入后的 HTML。
