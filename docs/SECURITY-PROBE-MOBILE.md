# happyboxSecurityProbe：手机部署、验收与安全审查

范围：用户已批准在现有环境手动部署只读核验函数。当前会话没有腾讯云部署身份，因此**没有代为部署**，没有修改生产数据、安全规则或现有 App，也没有构建 APK。真实环境核验仍待执行。

## 安全审查与加固

- 不开放 HTTP、网关 URL、定时触发器；仅使用 CloudBase SDK 函数调用。无登录、匿名、上下文 UID 不一致、环境不一致一律拒绝。
- 即使其他用户知道函数名，也只能获得拒绝结果。新增服务端 `HAPPYBOX_PROBE_ALLOWED_UIDS` 测试账号白名单，默认空名单、配置错误也拒绝，不读取数据库。最多允许 10 个真实 UID，不接受请求参数代替名单。
- 只在 `account_backups` 中按可信 UID 读取本人文档；没有 set/update/add/remove/delete/createCollection 或其他业务写操作，也没有接受任意路径/查询条件的接口。数据库事务的开始、提交等基础设施操作不等于修改业务文档。
- 不打印上下文、令牌、临时密钥或备份。仅向授权本人返回本人 UID、环境及核验状态，不返回昵称、邮箱、照片、完整备份或异常堆栈。平台自身仍可能记录调用、错误或认证活动元数据；不能保证整个云平台零日志。
- 检查返回式错误和抛出式错误，失败不能伪报读取成功。SDK 最多等待 3 秒，云函数配置总超时 8 秒，手动核验按需少量调用，不轮询。
- 原 SDK 3.18.7 依赖审计存在 5 项告警（4 high / 1 moderate），故不交付原依赖包。仅该独立探针改为服务端 SDK **4.2.1**，显式覆盖其 axios 为 **1.21.0** 并锁定依赖；现有 App SDK 完全不变。新依赖 `npm audit --omit=dev` 为 0 项告警，不代表不存在未知漏洞。
- 新 SDK 的事务、身份与上下文 API 已本地加载检查；19 项模拟通过。Axios 版本覆盖及 SDK 4.x 的真实 CloudBase 兼容性仍需本次只读调用验证，不能凭本地测试宣称生产可用。
- 依赖要求 Node.js **>=20.19.0**，建议控制台支持的 Node.js 22。若仅有 Node.js 20，先确认其实际补丁版本；不能满足时不要部署本包，反馈运行时选择后再适配。不要改变现有函数运行时。

## 一、手机保存部署包

[下载 HappyboxSecurityProbe-readonly.zip](https://raw.githubusercontent.com/kimizha/RandomToolbox/ui/android-happybox-redesign/deployment/security-probe/HappyboxSecurityProbe-readonly.zip)，保存到手机“文件/下载”。它是云函数部署包，**不是 APK**。已包含锁定的 node_modules，无需手机执行 npm 命令。

zip 根目录应直接有 index.js、probe.cjs、package.json、package-lock.json、node_modules，不需要把整个 RandomToolbox 上传，也不上传任何 APK 签名文件或腾讯云密钥。可根据交付的 SHA256SUMS 核对文件完整性。

## 二、控制台选择环境和测试账号

1. 手机浏览器进入腾讯云官方控制台 `https://console.cloud.tencent.com/`，选择“云开发 CloudBase”。必要时打开浏览器菜单中的“桌面版网站”，横屏操作。
2. 选择已有环境 **randomtoolbox-d5gg1p6rg1d2287eb**，地域 **上海 ap-shanghai**。不要新建环境、数据库或集合。
3. 在“身份认证/用户管理”找到你自己的既有测试账号，复制其 **UID**。不复制密码、token、SecretId 或 SecretKey。不要为探针注册新账号或编辑用户属性。
4. 只读查看现有函数/套餐剩余额度及运行时。若必须购买服务、增加角色授权或修改安全规则才能继续，停止并反馈；本次不批准这些额外变更。

## 三、新建并部署函数

1. 进入当前环境“云函数”，先查找是否已有 `happyboxSecurityProbe`。若同名存在，先查看其来源，不覆盖不明函数；仅更新可确认属于本次核验的版本。
2. 新建普通事件调用云函数，名称 **happyboxSecurityProbe**。不要选择 Web/HTTP 服务模板；不要新建 HTTP 触发器、公开访问链接、定时器或常驻实例。
3. 选择满足依赖要求的 Node.js 运行时；入口 **index.main**；超时 **8 秒**；内存选当前套餐支持的最小可用档（优先 128MiB）。不升级套餐。
4. 上传交付 zip，确认 index.js 位于代码根目录。包中已带 node_modules，关闭可选的再次在线安装/自动更新依赖；若控制台必须重新装依赖，要求按 lockfile 执行 npm ci，而非无锁升级。
5. 环境变量新增 **HAPPYBOX_PROBE_ALLOWED_UIDS**，值为 JSON 数组。例如下面的“实际UID”必须替换为控制台复制的值：

```json
["实际UID"]
```

保持为空数组 `[]` 可安全禁用探针。不填任何 SecretId、SecretKey、私钥、管理员密码或现有 App Publishable Key。

6. 沿用该环境已配置的云函数运行角色。若部署要求新增授权或自动授予宽泛管理权限，不直接同意，反馈具体提示。数据库原有安全规则保持原样。
7. 点击部署并等待状态完成。若运行时/依赖加载失败，保留探针关闭状态并反馈简短错误代码；不要通过更改数据库权限或去掉身份判断来修复。

## 四、先做无登录的负向核验

在函数“测试”页面，事件填 `{}`。控制台测试通常不带终端用户身份，预期返回 `REAL_USER_REQUIRED` 或 `TRUSTED_IDENTITY_UNAVAILABLE`；若平台未给环境上下文，也可能返回 `ENVIRONMENT_NOT_VERIFIED`。这些不能证明用户调用成功，但说明没有无条件放行。

再试以下伪造参数：

```json
{"uid":"other-user","role":"admin","explicitLogin":true,"context":{"TCB_UUID":"other-user"}}
```

仍应拒绝，不能因手填 UID 而读取备份。不要在控制台伪造运行时身份环境变量来制造成功。若无登录测试却返回真实身份已通过，停止使用并先检查平台是否确实注入了已认证的终端身份；不要扩大调用范围。

## 五、真实账号正向调用

必须通过**已有受信任来源中的 CloudBase SDK 会话**调用，不能只在控制台事件中填写 UID。代码如下：

```js
const response = await rtCloudApp.callFunction({
  name: 'happyboxSecurityProbe',
  data: {}
});
// 只查看 result，不打印 SDK session、access token 或 refresh token。
const result = response.result;
```

`rtCloudApp` 是当前项目在已登录页面中的 SDK 实例。登录账号 UID 必须在服务端白名单中；其他真实账号应返回 `PROBE_NOT_AUTHORIZED`，且不读取数据库。

**手机控制台本身不能代替 App 会话。** 当前 APK 没有探针调用按钮，本次也不修改 App 或构建 APK。若你没有现成的受信任测试网页/SDK 调用入口，可以先完成部署和负向测试，将结果反馈；正向调用需另行准备独立诊断入口并确认其托管来源。没有现成入口时，不能声称仅靠手机函数测试页已验证真实 UID；本次不擅自新增网页托管、安全域名或认证策略。

## 六、结果如何判断

| 字段/代码 | 含义 |
| --- | --- |
| identityVerified=true | 本次调用的可信 UID、用户信息与非匿名标志一致，且属于允许的测试账号。应与用户管理中的本人 UID 一致。 |
| transactionReadVerified=true | 事务内的本人文档读取返回有效响应。不代表文档一定存在，也不验证事务并发写冲突。 |
| READ_PREFLIGHT_COMPLETE | 身份与本次只读事务完成。返回的 ok 只用于这一探针，不代表 v3.0 安全验收通过。 |
| PROBE_NOT_AUTHORIZED | 用户不在服务器名单内或名单配置无效，不应放宽为所有用户。 |
| TRANSACTION_API_UNAVAILABLE | 当前加载的 SDK 没有对应事务方法。 |
| TRANSACTION_READ_NOT_VERIFIED | 读取失败、无效返回、缺失文档响应、IAM、网络等均可能造成；不能直接判定“不支持事务”。 |
| freshReauthenticationVerified=false | 探针未验证重新认证证明；不是证明服务不支持，也不是已经验证失败。 |
| concurrentWritesVerified=false | 本次没有写入与并发验证。 |
| perDeviceProviderRevocationVerified=false | 本次没有验证按设备撤销底层令牌。 |

### 可信重新认证证明的单独核实

检查所用服务端 SDK 身份上下文接口，其可见字段为 UID、登录类型等，尚未取得可验证的“刚完成密码/验证码认证”证明。单纯调用 signIn 成功、刷新 token、普通 iat 或客户端自行解码 auth_time 都不构成已验证的准入证明。

请在控制台对应认证产品说明或腾讯云官方支持中确认：

> 此环境使用 CloudBase JS SDK 3.x 的邮箱密码和邮箱/手机验证码认证。云函数能否取得由服务端验证的近期重新认证时间或一次性重新认证结果？如何验证签名/来源、绑定 UID、绑定挑战并防重放？是否支持撤销指定终端的底层 refresh/access token，撤销范围与生效时间是什么？

只需接口名称、官方文档及脱敏能力说明，不提供任何实际令牌或密钥。得到可验证接口前，该项保持“未核实”，双设备准入继续暂停。部署这个读取探针不会自行解决重新认证证明问题。

## 七、反馈与结束核验

反馈：部署状态、所选运行时、负向测试 code，以及（有真实 SDK 调用时）上述核验字段。UID 可遮盖，仅自己核对一致；不发送备份正文或完整认证响应。

核验完成后，将白名单改回 `[]` 或删除此独立核验函数；不要删除现有业务函数、集合或用户数据。每次少量调用仍占用云函数和数据库读额度，无高频监听，也不承诺零费用。

当前报告状态：静态审查、离线测试与依赖审计已完成；**部署、真实 UID、真实事务读取、重新认证证明均未在本会话完成**，待用户操作和反馈后更新报告。

部署包 SHA-256：`d97931bbc037dcecfeaff9b4a3dd77571f6a35d1ac3fb94043b8e19beb3eeef9`。压缩包大小 11119386 字节，仅独立云函数源码与公开 npm 依赖，不含 App 代码、账号凭据或签名文件。

后续临时测试构建入口、部署源码比对和真机判读见 [临时探针入口说明](DEV-PROBE-ENTRY.md)。入口源码已实现不代表线上部署版本已自动核实，亦未构建测试 APK。
