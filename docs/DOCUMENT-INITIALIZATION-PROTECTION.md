# Document 开通后的本机保护与一次性只读验收

适用分支：ui/android-happybox-redesign。基于 88fbe64；不修改 main。

## 当前事实与边界

用户已手动开通现有环境 randomtoolbox-d5gg1p6rg1d2287eb 的 PostgreSQL Document 插件，文档编辑器可以进入 pgdoc_data，集合管理显示为空，尚未手动创建 account_backups。这些是用户提供的控制台观察；本轮没有腾讯云管理连接，也没有读取线上实例。

已解决的是“当前所见 PostgreSQL 没有开通 Document 插件”的前置条件。不能据此宣称 SDK 默认路由、普通文档读取、事务能力或旧备份恢复已经通过。之前真实会话的 UID/环境核验结果仍有参考价值；本轮没有重复 V2/V3 云端调用。

开通插件不会把本机 LocalStorage、认证系统中的账号或其他实例的备份自动导入 pgdoc_data。“当前集合列表为空”也不能证明旧 account_backups 从未存在或已被删除。当前仓库只能证明代码意图访问该集合，不能证明某次历史上传确实成功。

## 发现的本机覆盖风险

旧 sync.js 每 5 秒读取 account_backups，用当前 UID 查询；没有文档时把所有远端值归一化为 null。当本机值等于上次成功同步基线时，rtSyncMerge 返回远端 null，rtSyncApply 会 removeItem。之后还会尝试 .doc(uid).set(...)，可能在空库上自动初始化备份。

因此不能仅凭“异常会捕获”判断安全：请求成功但返回空列表，恰好可能走入上述删除路径。

本轮源码修复：

- 增加源码控制的 RT_SYNC_CLOUD_PAUSED=true。在这一初始化阶段，登录、修改配置、联网、回前台、定时器、退出登录、手动同步均不能调用备份数据库。没有页面按钮、LocalStorage 开关或探针结果能够解除保护。认证 SDK 与真实 UID 来源不变。
- 保留原 schema:2 同步引擎和按 UID 的本机缓存；没有迁移或重建云端数据。以后解除暂停必须单独审查和批准，不是收到一次成功探针结果后自动恢复。
- 即便以后解除暂停，没有本人文档、values 全空或空对象的备份也会在应用远端值之前停止，不创建文档。缺失字段/null/空配置对象不再隐式删除本机对应键。
- 没有归属标记且没有目标 UID 缓存的旧本机配置，在保护阶段保持原样显示并留在游客缓存中，不猜测它属于刚登录的账号。已有归属的切换继续按 UID 隔离；游客配置仍只能由用户明确导入。
- 取消 5 秒轮询，保留 15 分钟前台低频触发；暂停期间该触发不会联网。修改仍立即落本机，不显示本轮“已同步”。

上述修改仅存在于仓库源码。已安装的 100159 等旧 APK 不会因此改变行为。当前先完全关闭旧 App，不卸载、不清数据；本轮遵守“不构建 APK”，因此尚不能在手机使用新增导出或宣称手机已受保护。之后需要另行批准同签名保护版测试包，才能安装到手机验证。

## 本机 JSON 备份

新增“设置 → 本机数据备份 → 导出本机 JSON 备份”，游客和认证失败时同样可用；账号同步面板也有入口。

导出格式 happybox-local-backup / formatVersion:1 / accountBackupSchema:2。storage 保存原始键值字符串，包括格式损坏但可能可恢复的本机 JSON；不对昵称、头像、转盘等进行重新序列化或默认值替换。

明确白名单：rt_settings、rt_wheelItems、rt_drawItems、rt_favorites、旧版 rt_history（若有）、hb_start_page、hb_party_local_v1、rt_sync_active_uid、rt_sync_guest_cache，以及 rt_profile_<UID>、rt_sync_cache_<UID>。覆盖上传头像、各账号保留的未同步配置和本机棋牌流水；旧收藏数组顺序原样备份，界面继续只显示一个常用工具。

SDK 登录会话、Token、密码和其他未知 LocalStorage 键不在导出白名单。不调用网络，不上传随机历史或账目。文件包含个人资料及本机保留的其他账号缓存，请保存到自己手机的下载目录并妥善保管；若在系统文件选择器主动选择云盘，文件提供方的行为由该选择决定。

Android 使用 ACTION_CREATE_DOCUMENT，用户选择具体文件，写完且关闭流成功才提示“已保存”。取消、文件写入失败不显示成功，不修改源数据，不申请广泛存储权限。最多 16 MiB UTF-8，读取失败中止整份导出，防止生成看似完整的半份备份。浏览器预览使用 Blob 下载，只提示下载请求，不冒充已写入磁盘。旧 APK 不具备原生保存接口时明确提示不支持，不走可能失败的 WebView Blob 降级。

本轮没有增加导入/自动恢复功能。备份可用于后续人工审查、恢复方案及迁移前校验；不要把文件直接整体写入 account_backups。恢复应确认 UID 归属并保留当前数据副本。

## SDK 检查结论

- App 在 inject_auth.py 中初始化相同环境、ap-shanghai；sync.js 使用 app.database().collection('account_backups').where({_id:uid}).get() 和 schema:2。没有 PostgreSQL 连接串或显式实例/database 选择参数。
- 现有 V3 部署 ZIP 锁定 @cloudbase/node-sdk 4.2.1，包含 @cloudbase/js-sdk 3.10.4 数据库模块；源码存在 Document GATEWAY 路由与默认 `(default)` instance/database 选择器，文档读请求走 `/database/instances/(default)/databases/(default)/collections/.../documents`。这证明存在访问 Document API 的实现路径，不证明线上映射和服务能力已验证。
- APK 构建脚本使用 @cloudbase/js-sdk@3，未锁定精确小版本。因此不能把探针锁定依赖版本直接当成某个已安装 APK 的实际 SDK 小版本。
- 没有在已审查数据库包中找到可直接调用的 listCollections/getCollections 公共方法，不编造此接口，也不为了列集合增加新探针。

## 一次最小只读验证方案（本轮不执行）

现在已知目标集合列表为空。立刻再次读取 account_backups，大概率仍得到 COLLECTION_NOT_FOUND；这不能分辨“路由未通”与“集合确实不存在”，因此不再重复这样的调用。

最少先做以下准备：

1. 保持旧 App 关闭、保留数据。后续如批准保护版 Debug 构建，同签名覆盖安装后先导出 JSON，抽查 nickname/photo/wheel/favorites 对应原始值确实在文件中。不要先启动旧版自动同步。
2. 在现有环境控制台只读记录：完整环境 ID、数据库实例 ID、数据库名称/类型、Document API 默认实例映射（若页面提供）、pgdoc_data 集合列表。界面不提供映射时，把这些非敏感标识与现有安全错误码交给腾讯云支持，**一次确认** SDK 默认选择器是否映射到刚开通的 PostgreSQL Document 服务，以及该组合的事务支持范围。无需重复探针。
3. 如果另一个既有实例有 account_backups，只查看集合名、当前规则和本人 UID 文档是否存在；不要导出到聊天、改规则、跨库复制或写入。在查明归属前不恢复自动同步。

取得默认路由依据后，只有两种可执行的安全路径：

- 若确认同一路由已有 account_backups：使用原已部署的 V3 和白名单真实 SDK 会话进行**一次**投影只读验收，不读取 values，不从普通页面同步。现有 V3 用同一 db/可信 UID 分别执行普通 doc.get 和只读事务，全部保留。无需部署新函数或新诊断字段。
- 若确认同一路由确实没有该集合：在“不创建集合”的本轮边界内，不能证明该集合的成功读取。需要用户以后单独批准并手动创建空的 account_backups 集合，审查其规则，保持没有业务文档、没有初始化写入，再执行上面的同一次只读验收。**本轮不创建，也不要求现在点击创建。** 空集合元数据的创建本身是变更，不能冒充只读操作。

验收判断：ordinaryRead.readVerified=true，diagnosticCode=DOCUMENT_ABSENT（或 DOCUMENT_PRESENT），才证明普通路径成功；事务还须 transactionReadVerified=true、code=READ_PREFLIGHT_COMPLETE、phase=COMPLETE，diagnosticCode=DOCUMENT_ABSENT（或 DOCUMENT_PRESENT）。V3 的普通成功结果没有独立的 code 字段，不应虚构额外成功码。修订标记匹配、UID 匹配或集合不存在均不算数据库通过；文档不存在是成功空结果，集合不存在是错误，两者必须区分。一次已具备路由/集合前置条件的验收仍失败时，保留安全码并转腾讯云支持确认 API/引擎兼容，不继续堆叠探针或盲改 SDK 参数。

## 双设备限制的启动条件

只读 API 成功不等于可以立即启用踢出。还需要：

1. 本机备份完成、旧数据位置/UID 归属和迁移方式明确。
2. 真实可信身份已验证；可信的主动重新认证证明仍需确认，不能信任前端“重新登录成功”或设备 ID。
3. 正式开发前，获批在隔离测试数据上验证事务写入、冲突重试和三设备并发上限；只读事务不证明这些原子写入能力。
4. 确定应用级会话数据和接口，所有受保护云函数逐次检查会话。底层设备 Token 撤销能力尚未核实，不能声称应用级踢出等于令牌失效。
5. account_backups 旧客户端直读/直写权限暂时保留，因此仍存在绕过新会话校验的通道。先明确兼容阶段边界；只有用户另行批准规则迁移、旧客户端处理与回退，才可声称完整强制限制。不能为过测提前封旧版或开启强制更新。

条件明确并获批后，可继续正式会话功能开发；本轮没有实现或启用设备踢出。

## 本轮自动化验证

- node scripts/check_sync.cjs：31 项通过。其中保护模式使用实际默认源码，明确断言登录/修改/网络/前台/计时器/退出的云端读取、写入均为 0；原有同步引擎回归仅在隔离 VM 内解除源码保护，不修改磁盘文件、不接触腾讯云。
- python3 scripts/check_local_backup.py：26 项离线浏览器检查通过，包含实际 JSON 下载、头像/缓存原样保留、凭据排除、未登录可导出、重复点击/取消/失败/成功回调、存储异常、UTF-8 字节限制及 320/390/768px 深浅主题。
- Android Java 源码针对 android-35.jar 编译检查通过。没有执行 Gradle、打包、签名或 APK 构建；系统文件选择器仍待获批后的 Android 真机验证。
- 原有 UI 回归 210 项、Debug 探针入口离线回归 37 项、发布限制检查 11 项全部通过。合计 315 项自动化检查；未将任何模拟结果视为真实云端或真机验收。

没有创建/修改集合、用户数据、安全规则、环境变量、云函数或 APK 更新配置，没有构建 APK、发布 Release 或触发真实账号同步。
