# 普通读取与事务读取对照探针 V3（待批准部署）

仅 ui/android-happybox-redesign；本轮只提交候选代码、测试和 ZIP。没有执行真实云端读取、部署函数、修改环境变量/权限、启用插件、创建集合、写入数据、构建 APK 或发布 Release。

## 只读检查结论

- 账号同步 `scripts/sync.js` 与原探针均使用 account_backups、_id=可信 UID，环境 ID 为 randomtoolbox-d5gg1p6rg1d2287eb；现有同步仍使用 schema:2，完全未改。
- SDK 为服务端 @cloudbase/node-sdk 4.2.1，依赖和锁文件不变；云函数数据库调用没有指定 instance/database，网关代码使用 SDK 默认选择器。
- 锁定 SDK 的事务启动是默认实例/数据库下的 /transactions，启动时还没进入 account_backups 读取。START_COLLECTION_NOT_FOUND 不能单独证明业务集合不存在。
- 原分类器只映射明确的错误代码，不根据错误消息猜测集合名；V3 也不把 START_COLLECTION_NOT_FOUND 自动解释成路由错误。
- 当前无腾讯云管理身份，不能确认实际实例、后端引擎、运行角色权限或插件状态，不能把本地检查当生产核验。

## PostgreSQL pgdoc / pgdoc_core 的关系

用户报告两个插件均未启用。这是当前所查看 PostgreSQL 数据库的状态，尚未证明它就是 CloudBase .database() 默认选择器对应的实例。

SDK 源码发起的是 Document API 网关请求，不包含当前项目显式的 PostgreSQL 连接串或 CREATE EXTENSION。若该环境实际把文档 API 路由到依赖 pgdoc 的 PostgreSQL 后端，插件状态可能影响相关能力；若账号备份属于独立的传统文档存储，则该 PostgreSQL 插件状态不能直接解释它的访问结果。

因此本轮不启用插件、不执行 SQL、不申请付费或变更权限。需在控制台/官方说明只读确认默认文档数据库实例与后端类型，以及该实例对普通 Document API 和事务入口的支持范围。对照测试只能缩小范围，不会自动识别物理实例或证明插件就是原因。

## V3 的最小操作范围

新候选源码目录：cloudfunctions/happyboxSecurityProbeComparison。**部署目标仍是已有 happyboxSecurityProbe，不是新增云函数。** 单独目录用于保留 V2 已审查源码、部署 ZIP 和当前 APK 摘要基线；原 V2 目录未改。

候选沿用同一初始化、身份/环境/匿名检查及 HAPPYBOX_PROBE_ALLOWED_UIDS 名单。只有这些检查通过，才调用一次 app.database()；普通路径和事务路径使用该同一个 SDK 数据库对象及可信 UID，不接受请求中的数据库名、实例名、UID 或角色。

1. 普通路径：db.collection('account_backups').doc(uid).field({_id:true,schema:true}).get()。
2. 事务路径：继续执行原只读 runTransaction；内部相同集合、UID 和投影。普通路径失败也继续独立检查事务，不以普通成功代替事务成功。
3. 结果只包含状态、固定安全码、文档是否存在等必要布尔值；不返回 UID、_id、schema 值、备份、请求头、密钥或原始异常/堆栈。
4. transaction 子结果保留 START/READ/COMMIT 阶段；ordinaryRead 单独报告。顶层原事务字段只代表事务路径，整体判断看 comparisonCode。
5. routing 仅声明代码请求 SDK_DEFAULT，resolvedBackendVerified=false；不伪称已定位实际实例。
6. 总诊断等待预算 6 秒，以配合现有 8 秒函数超时。超时不报告成功；普通读取预算耗尽后不再新启动事务。已经开始的只读 I/O 可能继续由 SDK 超时/运行时收尾，预算不等于强制取消远端请求。没有自动轮询或业务写入。

## 安全诊断与解释

| 观察 | comparisonCode / 解释 |
| --- | --- |
| 两条路径都通过 | BOTH_READS_VERIFIED；只证明本次两条只读路径返回有效结果 |
| 普通成功、事务失败 | ORDINARY_VERIFIED_TRANSACTION_FAILED；优先核实事务入口、能力、路由/协议兼容或事务权限差异，不证明某个原因已确定 |
| 普通失败、事务成功 | ORDINARY_FAILED_TRANSACTION_VERIFIED；保留两条结果，不把普通失败掩盖掉 |
| 两者未核实 | BOTH_UNVERIFIED；不能据此自动创建 account_backups |
| 超过预算 | PROBE_BUDGET_EXCEEDED；返回 budgetPhase，不猜测尚未完成的阶段 |

明确的 DATABASE_NOT_FOUND、DATABASE_INSTANCE_NOT_FOUND、INSTANCE_NOT_FOUND、INVALID_DATABASE_INSTANCE 才分类为 ROUTING_TARGET_NOT_FOUND。集合、权限、不支持、传输和未知异常继续各自分类；普通路径的不支持标为 READ_UNSUPPORTED，不冒充“事务不支持”。未知 provider 代码保守返回 UNCLASSIFIED_ERROR，不展示原文。

普通空数组/事务 null 均是正常空文档；错误式的集合不存在与正常空文档不同。未知、无效或其他 UID 的结果不得判成功。不通过未分类异常推断权限不足。

## 部署包与构建方式

[下载 HappyboxSecurityProbe-readonly-comparison-v3.zip](https://raw.githubusercontent.com/kimizha/RandomToolbox/ui/android-happybox-redesign/deployment/security-probe/HappyboxSecurityProbe-readonly-comparison-v3.zip)

修订：readonly-comparison-v3。包内含锁定 node_modules，根目录六个文件为 index.js、probe.cjs、transaction-read.cjs、read-control.cjs、package.json、package-lock.json。

ZIP SHA-256：`90a7958152e8372deea9d49a5a481a50029bb52e6616a622a5916efaf86b6d44`；大小 11,121,708 字节。

```bash
python3 scripts/package_security_probe.py /锁定依赖目录 输出.zip cloudfunctions/happyboxSecurityProbeComparison
python3 scripts/check_probe_deployment.py 下载的线上代码.zip cloudfunctions/happyboxSecurityProbeComparison
```

六个源文件与 ZIP 逐字节一致；包与依赖描述文件沿用原已审查版本。本轮依赖审计 0 项已知告警，不等于不存在未知漏洞。

## 自动化检查结果

- 17 项新对照场景通过：同对象/同 UID/同投影、双空结果、启动失败、两条路径独立、权限/路由/集合/不支持/未知错误、结果错误、提交失败、超时与脱敏。
- V3 原有身份/环境/名单套件 21 项通过，确认拒绝者不会进入数据库操作；只创建一次数据库对象。
- V3 事务套件 20 项通过。
- V2 原有身份套件 21 项、当前 APK 测试入口 29 项、原账号同步 22 项通过；保留 V2 基线，未修改账号同步或 APK 源码。
- 没有以模拟结果宣称真实 CloudBase 对照读取成功。

## 等待批准后的线上步骤

本轮**仍需要用户明确批准部署**。批准前不上传 ZIP、不改流量、不调配置。

获批后：保存现有 V2 代码 → 在既有环境、同名 happyboxSecurityProbe 上传 V3 ZIP → 保持 Node.js 20.19、index.main、名单、角色和数据库规则不变 → 不添加 HTTP/定时触发器 → 核对六个文件和 readonly-comparison-v3 → 用可信测试账号的实际 SDK 会话调用 data={}。

控制台 {} 不等同于匿名身份；无身份/非名单、伪造 UID 的拒绝测试仍保留。正向结果应分别检查 ordinaryRead 和 transaction；仅反馈安全状态字段即可。若需要权限变更、启用 pgdoc 或创建实例/集合，停止并另行审批。

**当前 Debug APK 100158 只支持 V2 修订和 V2 字段。** V3 部署后它会提示版本不匹配，不会正确展示完整对照结果，不能把这当作 V3 事务失败或成功证据。需要已有可信 SDK 诊断入口，或之后另行批准临时 UI 适配与测试 APK；本轮没有构建 APK。提前保留 V2 回退包，必要时恢复原代码，不动用户数据。
