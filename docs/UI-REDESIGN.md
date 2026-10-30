# 开心盒 Android UI

独立分支：`ui/android-happybox-redesign`。基线：`312fc6c`（包含个人资料、原始九种动物头像、账号自动同步）。基线之前的 `7987b08` 已有成功 Actions 构建：https://github.com/kimizha/RandomToolbox/actions/runs/41018504467 。最新同步提交通过了离线账号注入与 JS 语法检查；不把此前构建等同于最新提交构建。

## 设计与实现

奶白 / 炭黑底色，薰衣草紫主色，薄荷绿点缀；iOS 风格留白、分组与导航，卡通质感集中于工具插画和既有头像。首页突出用户已有常用与顺序，未收藏时提供明确添加入口。六款工具双列展示，收藏按钮独立于打开按钮。音乐、聚会、工具详情、资料、登录注册与设置保持相同视觉语言。

新增 `app/src/main/assets/ui/happybox.css`、`happybox.js`、`toolkit.png`；修改内置 HTML 布局、账号注入脚本的视觉模板、原生系统栏颜色与返回键处理、Manifest 键盘避让。UI 分支加入现有 APK Actions 推送触发范围，原有自动发布步骤仍仅限原开发分支。

`toolkit.png` 是参考用户提供图片生成的新插画图集。会话参考图没有可读取的本地原始文件，因此没有宣称直接打包用户原图。图集通过 SVG viewBox 显示各图标；导航与操作按钮使用原创线条 SVG。猜拳的石头、布使用配色一致的矢量手势，剪刀使用生成插画。未替换既有动物头像。

## 保留边界

- `scripts/sync.js`、`scripts/profile.js`、动物头像图集原样保留。
- CloudBase 环境、认证接口、云端结构和数据同步逻辑不变。
- 保留 applicationId、数据存储键、用户的常用顺序、转盘/抽签选项、设置、音乐文件与原有登录方式。
- 不修改 main 或既有开发分支。安装升级时仍须使用相同签名；不同签名不能直接覆盖安装，勿为安装而卸载含数据的现有 App。

## 验证

`python3 scripts/check_ui.py`：需要 Python Playwright 与 `/usr/bin/chromium`；在临时副本注入明确的离线占位 key，仅验证 UI，不访问真实认证或云端数据，不修改源 HTML。检查收藏持久化、320/360/390/430px 布局、六工具运行、深色模式、账号各页面与九种头像/资料保存。预览输出于 `docs/ui-preview/`。

另执行 JS/Python 语法检查与 `git diff --check`。未进行真实手机号/邮箱验证码、真实云端同步或 Android 真机测试。浏览器宽度检查不能代替 Android 系统栏与软键盘真机验证。

## APK

构建入口为 GitHub Actions 的 Build Android APK。工作区未提供 Android SDK、Gradle 或 CloudBase 发布 key，不能将带假 key 的离线预览作为可交付 APK。独立分支推送后的 Actions 使用仓库原有 secret 构建；APK 情况以最终报告中的实际构建结果为准。

验证结果：46 项浏览器检查通过，未捕获 JS 异常。首次 UI 提交 `64fcca1` 的 Actions 已完成账号 SDK 打包、账号注入、JS 校验、Debug APK 构建和上传：https://github.com/kimizha/RandomToolbox/actions/runs/41058329651 。之后的插画边界修正另由分支最新 Actions 验证。
