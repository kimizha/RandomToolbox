# TRANSACTION_READ_NOT_VERIFIED 排查与待批准修复

基线：3690e7a，ui/android-happybox-redesign。用户真机已验证真实 UID 一致，本次目标仅排查只读事务。没有更新线上函数、数据库权限或数据，没有生成 APK、发布 Release 或启用设备管理。

## 结论与证据

已确定一个真实代码缺陷，但尚不能仅凭旧返回码证明用户线上失败就由此造成：当前探针对成功响应 `data:null` 抛错；锁定服务端 SDK 4.2.1 使用的 JS SDK 数据库实现，事务 doc.get 会把零条文档转换为 `data: i[0] || null`。因此正常的不存在文档也会被误报为 TRANSACTION_READ_NOT_VERIFIED。

当前同一 catch 同时吞掉启动、读取、结果解析和提交错误。旧结果未保留这些阶段，无法事后从这个代码还原唯一真实原因，不能把权限不足或 SDK 不支持作为已确认事实。

检查了实际已安装的锁定依赖：`@cloudbase/js-sdk/database/dist/index.js` 的 DocumentReference._get、runTransaction、Transaction.init/commit/rollback。runTransaction(callback, retryCount) 会开始事务、执行 callback、再提交；任何阶段出错会抛异常或回滚。当前 callback 写法及 tx.collection(...).doc(uid).get() 链式 API 有实现依据。

`scripts/check_probe_sdk_contract.cjs` 直接读取锁定 SDK 源码，提取其空结果表达式在隔离 VM 执行，再以该形状复现旧探针误判、验证草案行为。没有初始化 SDK 或运行其网络传输。该检查不是实际云端事务验收；事务并发写入也未验证。

## 文档定位和空结果

- 现有同步使用 collection('account_backups').where({_id:uid}).get() 读取，用 doc(uid).set(payload) 写入。目标都是同一个 _id=UID 文档，正常情况下不是两套 ID。
- 事务 doc(uid).get() 的空结果为 data:null；非事务 where 查询常返回 data:[]。旧探针接受 [] 却拒绝 null，属于结果判断缺陷。
- 真实 UID 验证成功不等于此 UID 已有备份。首次登录、此前同步失败或尚未上传可能没有文档；不能为测试主动新建备份或用默认配置覆盖它。
- 若历史文档使用其他 ID，本次不搜索其他用户记录、不扫描全表、不修改 UID 绑定。可由用户在控制台只读检查 _id 是否等于本人 UID，无需提供正文或头像。
- 正常空结果并成功提交：事务读取可验证，documentFound=false；抛出的 DOCUMENT_NOT_FOUND 类错误不能假装完成提交，单独报告。集合不存在也不能当作文档不存在。

## 草案和测试（未接入线上入口）

草案为 `scripts/probe_transaction_candidate.cjs`，生产 index.js/probe.cjs 不引用它，已部署四个文件及现有部署 ZIP 完全未改。它仅用现有数据库、可信 UID 和只读事务：

1. 保留原身份校验和测试账号名单。
2. 使用 .field({_id:true,schema:true}) 投影，避免读取头像和整份配置。当前锁定 SDK 支持此 API。
3. 接受 data:null 或兼容的空数组为“未找到文档”，校验非空结果的 _id 必须等于可信 UID；缺失 data、错误类型或多条结果拒绝。
4. 记录 START / READ / COMMIT 阶段，成功提交后才能设置 transactionReadVerified=true。不执行写操作、不自动重试或创建集合/文档；runTransaction 的重试次数设为 0，减少核验调用和歧义。
5. 仅返回固定枚举，不输出 provider 原始 message、堆栈、请求正文、token、密钥或备份。未知代码归类 UNCLASSIFIED_ERROR，不能自动认定权限不足。

| 情况 | 安全 diagnosticCode | 读取核验 |
| --- | --- | --- |
| 事务方法缺失 | TRANSACTION_API_UNAVAILABLE | 未通过 |
| 回调内 API 形状不符 | TRANSACTION_API_MISMATCH | 未通过 |
| 明确的不支持代码 | TRANSACTION_UNSUPPORTED | 未通过 |
| 明确的权限错误代码 | PERMISSION_DENIED | 未通过 |
| 正常 null/空数组并提交成功 | DOCUMENT_ABSENT | 通过，文档不存在 |
| 本人文档并提交成功 | DOCUMENT_PRESENT | 通过，文档存在 |
| 抛出文档不存在错误 | DOCUMENT_NOT_FOUND_ERROR | 未通过，不假定提交成功 |
| 明确集合不存在 | COLLECTION_NOT_FOUND | 未通过 |
| 无效成功响应 | READ_RESULT_INVALID | 未通过 |
| 明确网络错误代码 | TRANSPORT_ERROR | 未通过 |
| 其余异常 | UNCLASSIFIED_ERROR | 未通过，需进一步受控排查 |

枚举映射目前只覆盖草案内明确列出的 provider 代码，不声称覆盖所有腾讯云错误代码。对未知错误保持未分类，不通过原始异常信息泄露内容。

18 项草案场景通过，涵盖 null/空数组、匹配/不匹配 UID、格式异常、启动/读取权限拒绝、提交失败、缺失 API、返回式错误和错误脱敏。原探针 19 项与账号同步 22 项模拟继续通过。源码契约检查通过，未取得新的真实云端诊断结果。

运行方式（仅本地，不连接腾讯云）：

```bash
node scripts/check_probe_transaction.cjs
node scripts/check_probe_sdk_contract.cjs /已安装锁定探针依赖的目录
node scripts/check_security_probe.cjs
node scripts/check_sync.cjs
```

## 建议的线上变更范围：等待批准

如获批准，准备同名 happyboxSecurityProbe 的新版只读实现：只替换结果判断、增加安全诊断枚举与阶段、增加最小字段投影；保留现有环境、入口、身份校验、名单、依赖锁、运行角色和数据库权限。增加固定 probeRevision 用于核对代码，不触碰用户数据。

为兼容旧 Debug APK，保留顶层旧 code（READ_PREFLIGHT_COMPLETE / TRANSACTION_READ_NOT_VERIFIED 等）并增加 diagnosticCode、phase、documentFound。现有 APK 100157 会过滤新增字段，所以可以观察空结果修复后事务是否成功，却不能直接展示细分失败原因。不能让用户以为旧 UI 没显示就说明服务端没返回。若仍失败，需要获准后单独扩展临时入口展示安全字段或使用受信任的 SDK 诊断入口；本轮不构建 APK。

获批后部署步骤：

1. 保存当前函数代码版本；保持当前名单和配置，不复制环境变量给聊天，不改变角色或规则。
2. 使用届时交付的新部署包更新同名 happyboxSecurityProbe，入口 index.main，保持 Node.js 20.19、依赖和超时配置；不新建 HTTP 或定时触发器。
3. 核对新版源码和固定 revision，再由原真实测试账号调用一次；只核对筛选后的状态和安全代码，不输出原始 SDK 响应。
4. 正常空读取且提交成功应报告读取成功和 DOCUMENT_ABSENT；如果未通过，根据安全 diagnosticCode 和 phase 再定位，不放宽权限。
5. 若更新异常，恢复保存的原函数代码版本即可；不回滚或删除用户数据。

当前仍在批准前阶段：没有替换生产函数源码，没有生成新的部署包，没有改现有 APK 临时入口。需要用户批准上述只读探针更新范围后再实施。
