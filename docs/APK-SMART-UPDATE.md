# 开心盒 APK 智能更新（B 方案）

此功能在 `ui/android-happybox-redesign` 实现。只替换现有 APK 检测入口，不依赖登录或 CloudBase，不下载/替换网页，不自动安装、卸载或清除数据，不自动上传蓝奏云或发布正式包。

## 远程配置位置

文件：`updates/version.json`。

当前客户端固定读取：

`https://raw.githubusercontent.com/kimizha/RandomToolbox/ui/android-happybox-redesign/updates/version.json`

请保留这个分支与路径。以前检测地址指向旧 `dev/cloudbase-auth-integration`；新机制统一读取 UI 分支，不在不同分支间回退，以免重新应用已撤销的策略。只改 `updates/**` 不会触发自动 APK 构建。

目前没有真实蓝奏云链接，默认：

```json
{
  "latestVersionCode": 100155,
  "latestVersionName": "2.9",
  "minSupportedVersionCode": 100155,
  "forceUpdate": false,
  "downloadUrl": "",
  "updateTitle": "开心盒版本更新",
  "updateMessage": "蓝奏云下载地址尚未配置，当前不启用强制更新。",
  "checkIntervalHours": 6
}
```

100155 是此前已交付版本的实际 versionCode。它是安全的待配置状态，不代表本次未发布的测试构建。不要照抄最初示例中的 `20`：这会低于现有 APK 的实际 code。

## 普通、强制与紧急关闭

1. 当前 APK code >= latestVersionCode：没有更新。
2. 当前 APK code < latestVersionCode，且未满足强制条件：普通提示，可“立即更新”或“稍后再说”。
3. `forceUpdate: true` 且当前 APK code < minSupportedVersionCode：原生强制更新页，只在获得有效的新配置和合法下载链接后生效。没有稍后、关闭入口；返回键被原生层消费，WebView 隐藏、停用，网页导航、摇一摇和恢复内置网页不能绕过。
4. **紧急关闭：把 forceUpdate 改为 false 并保存至同一文件。** 保留其他有效字段。下次启动、从下载浏览器返回、手动重试、网络恢复或自动检查成功后，旧版会恢复普通更新或无需更新状态。

强制开关为真正的 JSON 布尔值，不能写成字符串。版本 code 必须是正整数，最低支持 code 不得高于最新 code；间隔为 1～168 小时整数。版本名称为展示文本，判断始终使用 PackageManager 读取的实际 APK code（新 Android 用 getLongVersionCode），与网页版本无关。

空地址配合 forceUpdate=true 属于无效配置，永远不会启用强制锁定。空地址且最新 code 高于当前时，也不会显示无法完成下载的更新入口，而是提示配置暂不可用、允许继续本地功能。

## 以后更新下载地址

1. 确认正式 APK 构建、实际 code 高于上一发布版、固定签名一致。
2. 由你手动上传 APK 至蓝奏云，取得真实 HTTPS 分享页面地址。
3. 编辑 UI 分支的 `updates/version.json`，只把 `downloadUrl` 改为真实分享地址，并填写真实的 `latestVersionCode`、`latestVersionName`、更新标题和说明。
4. 普通更新保持 `forceUpdate: false`。需要拦截旧版时，填写适当 `minSupportedVersionCode` 后才打开强制开关。无需因此重建 APK。
5. 先用另一台旧版测试机检查普通更新、跳转和安装覆盖，再确认是否强制。

代码接受蓝奏云官方常用分享域名及其子域（lanzou.com、lanzoui.com、lanzoux.com、lanzouw.com 等 `lanzou[a-z].com`，以及 lanzn.com、lanznu.com、woozooo.com）。必须 HTTPS、不得带用户名密码或异常端口，不接受伪造后缀、javascript/file/http 链接。若未来分享服务改用其他正式域名，需要先核实并更新允许列表，不能直接放宽为任意链接。

点击更新会选择系统浏览器应用打开分享页，不在 WebView 下载、不抓临时直链、不登录蓝奏云、不发安装 Intent。若没有可用浏览器会提示重试，允许再次打开页面。密码说明如有需要可写在公开更新内容中，配置文件本身是公开的。

## 断网、失败与缓存

- 启动自动新请求一次；手动检查、下载返回和联网恢复强制刷新，避免沿用旧判断。
- 同时最多一个有效检查。网络在后台执行，连接和读取各限 4 秒，整体 UI 等待最多 12 秒；超时响应通过请求代号丢弃，不会覆盖较新的配置。
- 首次失败提供“重试”和“继续使用本地功能”，无有效新配置不判定版本过旧。
- 强制界面存在时若断网或检查失败，解除阻断，允许本地工具继续运行；这是 B 方案明确的离线降级，不把缓存当永久封禁依据。网络恢复再检查。
- 缓存仅显示上次获知信息，不能独立启动强制锁定。管理员关闭开关不会因旧缓存长期锁住用户。
- 成功后前台自动检查采用配置间隔；失败后前台按 1、2、4、8、15 分钟退避重试。后台停止周期轮询；反复自动失败只更新状态，不反复弹出打断。手动检查可绕过等待。
- 请求添加时间戳，禁止 HTTP 本地缓存，发送 no-cache/no-store。GitHub Raw 仍有地区可达性和边缘缓存限制，这不是对全网实时生效的承诺；如后续有稳定 HTTPS 静态托管，可调整 CONFIG_URL 及可信重定向规则，再构建一次客户端。普通下载地址与策略变更始终只需改 JSON。

## 原生界面与设置

普通卡片显示当前/最新版本、管理员标题与内容、立即更新和稍后再说；强制页为原生全屏拦截，没有关闭入口，并提供重新检查。失败页可重试或使用本地功能。尊重现有深色、动画速度与震动设置，长内容使用可滚动布局；版本信息不依赖网页资源。

设置原“检查 APK 更新”继续使用，新增失败后的重试入口；原有恢复内置网页功能仍保留，但不能绕过强制页。账号接口、CloudBase 配置、用户本地收藏/转盘/记账/头像等数据未改。

## 验证范围

- `python3 scripts/check_apk_updates.py`：使用生产 Java 策略与状态类执行 55 项离线测试，并按同一解析器验证仓库实际 JSON。覆盖新/旧/最低版本边界、普通可略过的状态、强制不可略过的状态、开关撤销、空链接、非法链接、异常 JSON、断网/超时放行、缓存不锁定、过期响应、合并请求、间隔与退避。
- 测试专用 org.json JAR 按固定 SHA-256 校验，**不作为 APK 新增依赖**；应用继续使用 Android 平台 JSON 类。
- 原生 Java 源码按 Android 35 接口编译检查；GitHub CI 使用正式 Android SDK 继续构建验证与固定签名检查。
- `:app:testDebugUnitTest` 加入 11 项 Robolectric 原生视图与生命周期测试：普通可跳过、强制遮蔽/停用 WebView、返回与外部点击、远程关闭、失败/空地址/异常 JSON/超时/缓存放行、未登录手动检查、浏览器 Intent 与返回后复查。使用离线传输替身，不访问实际下载地址；测试报告随 CI 保存。JUnit/Robolectric 只在测试使用，不打入 APK。
- 210 项既有界面回归、22 个账号同步模拟场景、7 项发布逻辑检查通过；没有访问真实账号数据。
- **还需真机验收**：原生界面在不同手机上的触摸/返回/横竖屏、真实系统浏览器、真实蓝奏云分享页、覆盖安装以及实际网络切换。逻辑状态测试不等于这些真机操作已经完成。

## 发布边界

旧 APK 不会仅因 JSON 文件改变而获得这套新机制，必须先安装包含此代码的新客户端。本次只做代码、测试和 CI 调试构建；正式 APK/Release 仍等待你确认，未上传蓝奏云。固定签名、applicationId 和 CI 递增 code 配置均沿用原设置。
