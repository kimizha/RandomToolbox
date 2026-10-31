# 账号恢复与固定签名

本次改动只在 `ui/android-happybox-redesign`，不修改 main、既有开发分支、CloudBase 环境 ID、认证接口或云端文档结构。

## 为什么以前更新需要卸载

原 Actions 直接在新的 runner 上生成 Debug APK，未配置固定签名私钥。同一个 applicationId 的覆盖安装必须使用相同签名；版本号也不能倒退。原 Debug 私钥未被持久保存时，不能从旧 APK 恢复私钥，也不能用新密钥无损覆盖旧证书的安装。

新的构建流程要求固定私钥才发布安装包。没有签名 Secrets 时只执行 Java/资源/脚本编译检查，不再发布每次换签名的临时 APK。CI versionCode 使用 `100000 + GITHUB_RUN_NUMBER`，版本名称 2.7；保持同一工作流序列，后续迁移工作流时注意版本号不能倒退。

## 一次性设置 GitHub Actions Secrets

仓库 Settings → Secrets and variables → Actions → New repository secret，添加：

| Secret 名称 | 内容 |
| --- | --- |
| ANDROID_KEYSTORE_BASE64 | 私密签名包中同名 txt 全部内容 |
| ANDROID_KEYSTORE_PASSWORD | 私密签名包中同名 txt 全部内容 |
| ANDROID_KEY_ALIAS | 私密签名包中同名 txt 全部内容 |
| ANDROID_KEY_PASSWORD | 私密签名包中同名 txt 全部内容 |

如果已有正式签名私钥，优先使用原密钥，不必生成新密钥。新的可选私密签名包保存在工作区仓库以外，未提交 Git。切勿把签名包或密码发布到仓库、Issue 或公开聊天。

也可以在有权限的本机用 GitHub CLI 登录后执行：

```bash
python3 scripts/install_android_signing_secrets.py /你的私密签名包目录 kimizha/RandomToolbox
```

当前会话访问仓库 Secrets 返回 Forbidden，因此未能代写这些 Secrets。设置后重新运行 Build Android APK，流程会验证密钥、签名并打印 APK 的公开证书指纹，方便核对后续版本使用同一证书。首次从旧临时签名切换到固定签名仍需迁移，先确认云端备份成功，不要为了安装而直接删除尚未同步的数据。

## 配置同步修复

继续使用原 `account_backups` 集合、`schema: 2` 与 `{values, updatedAt}`；同步字段只有：

- `rt_settings`：声音、震动、主题、速度等设置。
- `rt_wheelItems`、`rt_drawItems`：转盘和抽签的选项。
- `rt_favorites`：常用工具及顺序。
- `rt_profile_<UID>`：昵称、头像。

登录会立即启动恢复，不再等 5 秒定时器，也不再新建默认个人资料覆盖云端内容。普通设置和个人资料保存后，会在约 400ms 内发起同步；离线先按 UID 缓存，联网/重新登录后重试。退出登录前尽量完成上传，最多等待 3 秒，网络不通时仍保留本机缓存。

合并会保留本机未上传的改动；设置、个人资料按字段合并，防止本机默认值盖掉云端的昵称、头像或其他设置。不同账号、过期网络响应相互隔离。之前没有绑定账号的游客配置保留在本机，通过“账号同步 → 导入本机游客配置”显式导入，不自动把其他账号可能留下的无归属配置上传。

“账号同步”现在有实际页面，显示状态、最近成功同步时间、具体失败原因与立即重试按钮。只有云端读写成功才显示完成。权限不足、集合不可用、格式错误、头像过大不会显示成同步成功，也不会无提示丢弃本机修改。会员资格不包含在客户端配置白名单里，不通过这些偏好字段授予权益。

## 验证和恢复边界

- `node scripts/check_sync.cjs`：21 组模拟云端场景，包括重新安装恢复、离线后重试、切换账号、默认资料覆盖保护、读写失败、头像大小及竞态保护。没有读取或修改真实云端数据。
- `python3 scripts/check_ui.py`：137 项浏览器检查，包括短屏上转盘开始按钮位于底部导航之上，配置按钮与标题同行，三行示例及同步入口。
- 固定签名预检已验证未配置/部分配置/完整密钥三种情况。
- 真实 CloudBase 权限与真实账号跨设备恢复仍需账号实测；若状态提示权限拒绝，需要管理员核对现有集合对当前 UID 的读写权限，不应开放公共读写。本次没有修改云端安全规则。
- Android 覆盖安装仍需使用实际固定签名 APK 在手机上验证。若旧版本已卸载且数据当时未上传，无法从新安装中找回已删除的本机配置。
