# 只读探针事务修复包 v2

仅 ui/android-happybox-redesign。用户已批准准备此更新包，尚未在本会话部署线上函数。没有修改 APK、同步逻辑、权限、用户数据或设备会话功能，没有构建 APK 或发布 Release。

## 下载与变更

[下载 HappyboxSecurityProbe-readonly-tx-null-v2.zip](https://raw.githubusercontent.com/kimizha/RandomToolbox/ui/android-happybox-redesign/deployment/security-probe/HappyboxSecurityProbe-readonly-tx-null-v2.zip)

已带锁定 node_modules，大小 11,120,452 字节，手机无需 npm。zip SHA-256：

`aefc4a54a767ed17bda4cdabc502fc614a8682d7bd8fdf5c4a8e7163183a7370`

修订标记：`probeRevision: readonly-tx-null-v2`。所有响应（含身份拒绝）均带该固定标记，不包含额外私人数据。

- probe.cjs：保留原身份、环境、匿名与服务端 UID 名单检查，接入结果分析和修订标记。
- transaction-read.cjs：新增只读事务分析，读取范围仅 account_backups.doc(可信 UID)，投影 {_id:true,schema:true}。
- data:null/空数组正常表示没有文档；只有事务提交完成后才返回读取成功。本人文档 _id 不匹配、响应缺失、无效格式拒绝。
- phase 区分 START、READ、COMMIT；diagnosticCode 为固定分类，stageCode 是阶段与固定分类组合，不带原始错误信息。例如 START_PERMISSION_DENIED、READ_PERMISSION_DENIED、COMMIT_PERMISSION_DENIED、COMMIT_TRANSPORT_ERROR。
- 没有事务写入、自动建表、插入或补默认资料；重试次数为 0。没有日志输出、HTTP/定时触发器或新入口。
- index.js、package.json、package-lock.json 未改，入口、3 秒 SDK 超时、SDK 4.2.1、axios 覆盖 1.21.0 与原包一致；未增加依赖或权限。

## 自动检查结果

- 21 项探针集成模拟：身份、匿名、环境、白名单、投影、UID 绑定、正常 null 与错误脱敏。
- 20 项事务场景：正常空记录/本人记录、错误响应、缺失 API、不支持、文档/集合不存在、权限拒绝、网络和提交失败。
- 锁定 SDK 源码契约检查通过：明确验证事务空结果表达式产生 null。不是实际云端 SDK 事务验收。
- 原 22 项账号同步模拟通过；17 项临时入口/源码比对检查通过。
- zip 中五个源文件逐字节与仓库一致；依赖审计 0 项已知告警（不是无未知漏洞保证）。

测试未改生产数据；模拟不能作为线上修复已成功的证明。原来的泛化返回码无法唯一证明用户上次失败就是空文档，v2 用于进一步安全定位。

## 手机同名更新步骤

1. 下载上方新 ZIP 到手机文件。不要选旧的 HappyboxSecurityProbe-readonly.zip；旧包保留作为回退用。
2. 腾讯云控制台 → 云开发 CloudBase → 既有环境 randomtoolbox-d5gg1p6rg1d2287eb / 上海 → 云函数 → **已有 happyboxSecurityProbe**。不要新建环境或业务集合。
3. 先下载保存当前线上代码，记录现有入口 index.main、Node.js 20.19、8 秒超时、运行角色、UID 名单和流量。不要导出或发送凭据；不修改这些配置。
4. 上传 v2 ZIP 更新代码，根目录必须有 index.js、probe.cjs、transaction-read.cjs、package.json、package-lock.json、node_modules；使用 ZIP 自带锁定依赖，不重新升级 npm 包。
5. 保留 HAPPYBOX_PROBE_ALLOWED_UIDS 现有测试名单；不添加 SecretId/SecretKey，不调整数据库规则或角色授权，不增加 HTTP/定时触发器。
6. 部署完成后核对执行方法、运行时与实际代码；按原机制让已确认的更新版本接收测试流量，不更改其他函数流量。若需要新增授权或付费服务，停止并反馈。
7. 可下载当前代码包运行 `python3 scripts/check_probe_deployment.py 代码包.zip`；现在校验五个文件（含新增 helper）。手机编辑器至少确认 revision、helper 存在、身份检查、最小投影与安全返回。若部署异常，恢复保存的旧函数代码即可，不回滚用户资料。

## 更新后的安全测试

**先检查版本和拒绝路径**：控制台事件 {} 不保证没有平台身份。无真实终端身份应被拒绝；平台若注入了身份但不在名单，会返回 PROBE_NOT_AUTHORIZED。响应应含 readonly-tx-null-v2。再次填入伪造 uid/context/role，不能改变身份或权限，不输出备份内容。

**真实账号路径**：通过现有 SDK 会话调用同名函数，data 仍为 {}；当前 UID 必须在服务器名单，不传 UID 选择文档。正常结果示例只展示非敏感核验字段：

```json
{
  "probeRevision": "readonly-tx-null-v2",
  "identityVerified": true,
  "code": "READ_PREFLIGHT_COMPLETE",
  "transactionReadVerified": true,
  "diagnosticCode": "DOCUMENT_ABSENT",
  "documentFound": false,
  "phase": "COMPLETE"
}
```

DOCUMENT_ABSENT 代表正常读取但不存在本人备份，不需要为了测试新建记录；DOCUMENT_PRESENT 代表存在。二者均须提交成功。可在控制台只读核对本人 _id 是否存在，不复制正文或头像。

若仍失败，反馈 probeRevision、code、phase、diagnosticCode、stageCode 即可。未知 provider 错误保守归为 UNCLASSIFIED_ERROR，不输出其 message、stack、token 或配置。不要为复现权限错误修改生产规则；失败路径已由模拟覆盖。

**现有 Debug APK 100157 的兼容性**：保留原顶层 code，因而可显示修复后的读取成功/失败；但它不会显示新增诊断字段和 revision，确认框仍引用此前 813c2f5 的核对记录，不能据此证明新版源码一致。本页的五文件比对才适用于 v2。要完整查看阶段码，需已有受信任的 SDK 调用入口读取筛选字段，或以后另行批准临时 UI 更新；本轮没有改 APK。

重新认证证明、并发写入、底层设备令牌撤销仍保持未核实；这次成功读取不能作为正式双设备功能上线依据。

## 源码摘要

| 文件 | SHA-256 |
| --- | --- |
| index.js | d0e686bf2b6c52f45b9f0368a045ee270fd1e3d6d6dcc83893e90cd5be62a812 |
| probe.cjs | 5ee9760001d35ff0fc55e74bb38c08779b175f8871677842cf584b81a217afa8 |
| transaction-read.cjs | ddd3e49c6b1f2081d89edb98fb539a50d24a58601569b53ab469672365dc7d34 |
| package.json | 25a65f02f2b92bd997fbb8b1f46a62de6e95881ce7442839d8666950b0a318c4 |
| package-lock.json | 2ef86562af26d38ccdbfbd727b7217aa9b15857197403ecc428dc51841c5ddd7 |
