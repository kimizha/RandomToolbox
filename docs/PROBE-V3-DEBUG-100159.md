# V3 只读对照入口 Debug APK 100159

本次只适配 UI 分支的临时测试入口并构建 Debug，不修改已部署的 happyboxSecurityProbe、环境变量、权限、账号同步或设备功能。

## 下载与身份校验

- [Actions 构建记录](https://github.com/kimizha/RandomToolbox/actions/runs/41310888452)：成功。
- [下载 Debug APK 附件](https://github.com/kimizha/RandomToolbox/actions/runs/41310888452/artifacts/13084658987)：登录 GitHub 后下载 ZIP，解压安装 app-debug.apk。
- versionName 2.9；versionCode 100159；package com.randomtoolbox.app；debuggable=true；包含专用探针入口。
- APK 源提交：39827c5ff255f52e67cb110a05501e093467e18b。
- 固定证书 SHA-256：714524c73030e3d5010c849f52012af5adc7f36ecc2b0013ec6bff4c8324fa4b。
- APK SHA-256：7e7da6a16101a85b9dc417e555ddd4039282181a422655d23329fcbd5b11b591。
- 构建前及构建后比对已交付固定证书，不允许临时签名替代；两个 Release 发布步骤均跳过。

## 改动与安全范围

scripts/dev-security-probe.js：分别判读 ordinaryRead、transaction；展示事务启动、读取、提交状态和 phase/diagnosticCode/stageCode/code；验证字段及 comparisonCode 一致性，拒绝将旧版本或缺失结果当成功。

scripts/security_probe_manifest.py：绑定 eb0734c 的 V3 部署 ZIP 和六个源文件，使用实际 SHA-256 与 readonly-comparison-v3。默认“线上版本尚未核实”，修订标记匹配不代表远程源码摘要或数据库读取成功；不自动勾选人工确认。

scripts/check_dev_security_probe.py：37 项入口模拟，包括两条结果独立、空文档、START/READ/COMMIT 失败、预算超时、无会话、拒绝名单、旧版本、结果缺失/矛盾、错误脱敏、源码摘要及正式版隔离。

scripts/verify_signed_apk.py：要求测试 code 高于 100158；保留固定证书、包名、Debug 与测试入口校验。

.github/workflows/build-apk.yml：增加 V3 身份与对照测试，沿用专用 Debug 开关；不改变普通构建默认模式与发布保护。

不修改 app 业务 HTML、登录逻辑、云同步结构、收藏、转盘、头像、随机历史或云函数。默认普通构建不注入探针脚本；正式打包/发布路径仍拒绝探针包。

## 手机测试

1. 保留原 App，下载本页新附件并直接覆盖安装。不卸载、不清数据。
2. 打开设置，找到“开发测试 · 只读安全核验”。若原会话有效则复用；否则使用原登录界面登录获准测试账号，不向探针输入 UID 或凭据。
3. 展开本地部署摘要，按实际线上源码核对后手动确认。调用仍为当前真实 SDK 的 happyboxSecurityProbe，data={}，没有客户端 UID 参数。
4. 点击一次核验，等待结果。默认不调用、不轮询；重复点击合并，退出或切账号后丢弃旧响应。
5. 分别记录【普通读取】和【事务读取】中的安全状态及代码，再看“对照判读”。不发送原始响应、文档正文或认证 token。

## 结果解释

- PROBE_NOT_AUTHORIZED：服务端拒绝当前调用，不表示数据库读取成功。控制台显示此码也不能替代真实手机会话测试；不通过前端修改或放宽数据库权限解决。
- BOTH_READS_VERIFIED：普通与事务子结果均有效且与总结果一致；DOCUMENT_ABSENT 为正常空文档，无须创建记录。
- ORDINARY_VERIFIED_TRANSACTION_FAILED：普通读取已通过、事务仍失败。例如 START_COLLECTION_NOT_FOUND 时显示事务启动未通过，读取、提交未执行；不要据此创建集合或宣称事务成功。
- ORDINARY_FAILED_TRANSACTION_VERIFIED：显示两条不同结果，不隐藏普通路径的失败。
- BOTH_UNVERIFIED：分别检查安全代码，不直接猜测权限或插件原因。
- PROBE_BUDGET_EXCEEDED / UNKNOWN：阶段不确定，不伪称未执行或已成功。
- READ 阶段失败：启动已完成，读取未通过，提交未执行。
- COMMIT 阶段失败：启动、读取已完成，但提交未通过，不把读取中间结果当事务成功。
- 修订匹配、身份成功但缺少 ordinaryRead/transaction：保持“尚未核实”。最终顶层 code 仍是服务端事务兼容结果，不代表两条读取都成功；整体还需 comparisonCode 与子结果一致。

V3 为隐私保护不返回 UID。界面明确显示当前 SDK 会话已确认，以及服务端报告内部身份校验是否通过，不伪造客户端与服务端 UID 的逐值比较。环境仍须与既有环境匹配；额外返回不匹配 UID 时拒绝确认读取成功。

实际数据库实例、PostgreSQL 插件状态、重新认证证明、设备限制和令牌撤销仍未核实，本轮没有相关配置变更。

## 检查结果

37 项入口模拟、17 项 V3 对照、21 项 V3 身份套件、20 项事务场景、22 项同步模拟、210 项现有界面回归、11 项发布/身份保护、2 项构建前签名检查均通过。Actions 的原生测试、55 项 APK 更新策略、APK 构建与签名检查通过。没有失败检查。

以上是自动化与构建结果，不宣称真实 CloudBase 读取或事务已成功；需要用户按上述步骤手动调用并反馈两条诊断结果。
