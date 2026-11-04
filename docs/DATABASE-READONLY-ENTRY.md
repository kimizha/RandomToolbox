# 手机端一次点击的 V3 数据库只读验收入口

仅在 ui/android-happybox-redesign 开发，基于 100160 的数据保护代码。目标为 Debug 测试包，不发布 Release，不修改腾讯云资源。

## 使用

使用同固定签名的新 Debug APK 覆盖现有安装，不卸载、不清数据。进入“我的”页面，向下找到“开发测试”，点击“数据库连接测试（只读）”。有效会话会直接复用，无需再次登录或输入 UID、Token、密钥；会话无效只提示本次未调用函数，不自动跳转登录、不创建账号。

检查完成可点击“复制诊断摘要”。摘要只含固定状态、阶段和经过白名单过滤的诊断代码，不含 UID、邮箱、照片、备份正文、Token、密钥或原始异常。复制之后可反馈摘要，不需要发送本机备份。

## 实际 SDK 接入方式

inject_auth.py 仍通过原 rtStartAuth 创建相同 CloudBase app/auth 实例。仅在 HAPPYBOX_SECURITY_PROBE_TEST=1 时，在原实例创建位置加入受保护的附件调用，向 probe-context.js 传入实际实例及账号/暂停状态读取闭包。新的 UI 和适配器不猜测 rtCloudApp、rtAuth 等全局变量，不创建第二个 SDK、认证实例或登录上下文，不拼接 HTTP 身份请求。

probe-context.js 在调用前读取原认证实例的 getSession，确认 SDK 会话与当前 App 账号一致，再调用同一 app.callFunction({name:'happyboxSecurityProbe',data:{}})。返回后再次检查会话、账号及同步暂停状态，账号切换/退出或实例切换即丢弃结果。客户端会话检查不代替服务端鉴权，真实 UID、非匿名、环境及名单仍由既有 V3 云函数验证。

每次只由用户点击触发，不启动轮询。运行时禁止重复点击；界面 12 秒超时后结束加载，但直到原 SDK 请求真正结束前仍禁止重试，不制造重叠请求。旧响应不会把超时改成成功。

## 结果解释

身份与版本、普通读取、事务读取分别用卡片展示。成功结果必须同时满足身份/环境/修订检查、明确布尔值、文档存在性与诊断码一致，以及 V3 总结果与子结果一致。

| 页面综合状态 | 含义 |
| --- | --- |
| BOTH_READS_VERIFIED | 两种读取的有效证据及综合结果一致 |
| ORDINARY_READ_FAILED | 普通读取失败或证据不完整；独立保留事务结果 |
| TRANSACTION_READ_FAILED | 事务失败或证据不完整；独立保留普通读取结果 |
| BOTH_UNVERIFIED | 两种路径未通过、缺失证据或综合结果矛盾 |
| PROBE_NOT_AUTHORIZED | 未确认有效 SDK 会话，或服务端身份/名单未通过；以分区说明区分 |
| PROBE_REVISION_MISMATCH | 修订缺失或不等于 readonly-comparison-v3，停止重复调用 |
| PROBE_FUNCTION_NOT_FOUND | SDK 明确报告函数不存在，停止；不部署或切换其他入口 |
| SDK_NOT_READY / SESSION_CHECK_FAILED / PROBE_CALL_FAILED / PROBE_TIMEOUT | 初始化、会话、调用或时间预算未完成；不输出原始错误 |

DOCUMENT_ABSENT + documentFound=false 是成功的空文档证据。普通成功没有独立 code，事务成功为 READ_PREFLIGHT_COMPLETE、phase=COMPLETE；成功 stageCode 显示“不适用（成功）”。START 失败显示读取/提交未执行；READ 失败显示启动完成、提交未执行；COMMIT 失败不会伪装成事务成功。

V3 在服务端同次调用中先做普通读取，再做只读事务；普通读取失败时也会尝试事务。没有加入“仅普通读取”的不存在参数，没有修改服务端流程。事务只执行开始、投影读取、只读提交，不包含业务写操作。

## 安全边界

保持 RT_SYNC_CLOUD_PAUSED=true，保留本机 JSON 备份、空云端保护、schema:2 和 UID 归属缓存。scripts/sync.js、profile.js、local-backup.js、MainActivity.java、AndroidManifest.xml、cloudfunctions 和 updates 均没有改动。

取消旧测试 UI 的手工勾选步骤以实现单次点击，但没有自动勾选或宣称源码已核实。页面仍注明“线上源码摘要尚未核实”；运行时修订匹配只是版本协议检查，不等于逐文件验证线上 $LATEST，也不等于数据库成功。本轮没有腾讯云部署/管理权限和真实测试会话，不能确认线上当前包或宣称真实 Document API 已通过。

函数缺失、版本不匹配、身份拒绝均明确提示并停止，不放开 ADMINONLY、不修改名单、角色、环境变量、数据库或函数，不导入 JSON，不创建文档、不启用双设备限制。只读成功也不证明并发事务写入、可信重新认证或底层设备令牌撤销已核实。

## 文件与删除方式

- scripts/probe-context.js：新增测试专用 SDK 实例适配器。
- scripts/dev-security-probe.js：复用原临时入口文件，改为单按钮、分区结果、严格判读、加载/并发保护和脱敏复制。
- scripts/dev-security-probe.css：新增测试卡片样式，使用现有主题变量，兼容深色、小屏和减少动画偏好。
- scripts/inject_auth.py：仅显式测试构建注入适配器/样式/入口及初始化附件；正常构建不包含这些代码。
- scripts/check_dev_security_probe.py：55 项完整注入页面的离线集成测试，替换旧勾选式测试。
- scripts/data_protection_build.py、check_data_protection_build.py：支持受保护的只读探针包，构建前核对实际资产、原资料逻辑及 SDK 附件；旧包基准更新到 100160。
- scripts/prepare_ci_signing.py、verify_signed_apk.py、check_probe_signing.py、check_release.py：固定签名、递增版本、覆盖安装及 Release 拒绝检查。
- .github/workflows/build-apk.yml：只读入口浏览器测试、受保护 APK 构建前后核验，测试附件命名。
- docs/DEV-PROBE-ENTRY.md、本文件：新旧临时入口说明。

后续删除整个临时入口时，移除 inject_auth.py 中 HAPPYBOX_SECURITY_PROBE_TEST 分支及三份测试入口文件，清理其测试与工作流显式开关；原登录、资料、备份与同步业务不依赖这些测试模块。不得为移除入口清除应用存储。

## 已完成自动化检查

55 项入口集成、27 项构建保护、15 项发布限制、2 项签名保护、31 项同步回归、26 项本机备份检查，共 156 项通过；全部是隔离测试，无真实 CloudBase 调用。测试包括调用失败、缺失函数、V2/缺失修订、权限拒绝、普通/事务失败、空文档、原始错误脱敏、复制、切换账号、超时与重复点击、320/390/768px 深浅色布局。

另已核对 V3 本地 ZIP 与六份源文件一致，未改其内容。APK 交付后的真实结果须由用户使用手机现有白名单账号点击获得，不能把以上模拟结果当作云端验收。
