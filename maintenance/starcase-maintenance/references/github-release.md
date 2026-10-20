# GitHub 发布、镜像与更新

## 当前状态和边界

v0.1.1 配置独立发布源 `https://github.com/Feathercatttt/starcase-archive`，并启用 `UPDATE_PUBLISHED=true`。用户已授权公开发布 EXE / APK 和线上更新；每次仍先核对实际仓库、最新 release 与 raw 清单，不能只凭本地文件判断已上线。旧 v0.1.0 false 原型需手动安装首次启用版。

用户要求把上传 GitHub 和后续更新也交接到本 skill。真正上传按该轮明确发布任务与已有授权执行；小功能本地修改无需擅自发布，也无需因 skill 再增一次确认。

## 版本与身份

发新版同步更新：

1. `src/model.js` 的 VERSION。
2. `native/windows/UpdateProtocol.cs` 的 Current。
3. `native/android/src/com/starcase/archive/UpdateProtocol.java` 的 CURRENT。
4. `native/android/AndroidManifest.xml` 的 versionName，versionCode 严格递增。
5. `tools/build-native.py` 写入 `service/version.json` 的版本；README 版本和更新说明。

若更换候选仓库，Windows / Android 的 Repo/REPO 与 ManifestUrl/MANIFEST 一起改，严格地址校验也依赖这些常量。已有发布后不随便改包名、数据库名、WebView origin 和签名身份。

私钥位置：`private/signing/update.pem`；Android 为同目录 `starcase-release.p12` 与凭据文件。只读使用，不打印，不上传，不放进 Actions 日志。**已有应用签名密钥丢失后，重新生成不能覆盖安装旧 APK**。`outputs/更新公钥.json` 和源内公钥可公开。

## 本地可审阅的发布产物

先做源代码修改、版本同步、针对性测试和双端构建：

```powershell
python -X utf8 tools/build-web.py
python -X utf8 tools/build-native.py windows
python -X utf8 tools/build-native.py android
python -X utf8 tools/package-release.py --sign --full
```

发布说明可用 `--notes-file release-notes.md` 指定 UTF-8 文本，避免新版仍沿用首版说明。

`outputs/release-vVERSION/` 包含：

- `Starcase-Windows-Update.zip`：内部必须为 `Starcase-Update/星匣.exe`、`星匣.html`、`service/server.py`、`service/version.json` 及必要程序依赖。排除大 WebView2 安装器和任何用户资料。
- `Starcase-Android.apk`：正式非 QA APK，包名 com.starcase.archive。
- `stable.candidate.json`：本地签名候选，不自动生效。
- `payload-preview.json`：供审阅的明文清单，不作为客户端更新清单。
- `checksums.json`、使用说明和模板定义。

客户端附件 URL **固定**为：

```text
https://github.com/OWNER/REPO/releases/download/vVERSION/Starcase-Windows-Update.zip
https://github.com/OWNER/REPO/releases/download/vVERSION/Starcase-Android.apk
```

发布标签、清单版本、两个附件名和实际程序集版本须一致。更新包下载上限 128 MiB；Windows 解包总大小上限 240 MiB、单文件 80 MiB。完整手动安装包可大于此限制，但不能当自动更新附件。

## 签名协议

客户端接受 `{payload:base64,signature:base64}`。payload 是**实际 UTF-8 JSON 字节**，RSA PKCS#1 v1.5 + SHA256 签名，不能在签名后重新排版 payload。

明文 payload 包含 app=starcase-archive、schema=1、version、notes、windows、android；每个平台含 URL、size、sha256，Android 另含 package、versionCode。脚本从当前产物计算。客户端验证发布签名、地址归属、文件大小与 SHA256，并阻止降级。Windows 独立更新器复验后备份替换，失败尝试回滚；资料目录不在更新目标内。

`python -X utf8 tests/release.py` 检查本地签名候选、附件哈希、正式 APK 与源码打包边界，并用实际 C# 协议验证签名、拒绝篡改。没有发布到互联网就不能声称已验证镜像下载与在线安装。

## GitHub 上传流程

先确定正在使用的 GitHub 身份和目标 repo。浏览器已登录不代表 gh 已认证；使用可用连接器或 gh 的正常授权状态，不读取/打印浏览器令牌。本机 gh 若不在 PATH 可定位已安装版本；CLI 命令仅是示例，可使用等价结构化工具。

1. 第一次正式启用时，准备独立仓库，源代码只提交 src/native/tools/tests/maintenance 与必要说明。核对 staged 文件；`.gitignore` 不会自动移除已追踪私钥。不要 `git add .` 后直接推送。
2. README 写明 AI 辅助代码、功能表、使用方法、支持系统、数据备份、当前已知限制；个人飞书样本不进入公开仓库。
3. 把已测试提交推送并建立对应 tag。用 release 草稿先上传固定名更新包、正式 APK、完整/轻量手动安装包、源码与使用说明。多行发布说明用 UTF-8 文件和 `--notes-file`，不要拼接转义字符串。

```powershell
gh release create vVERSION --repo OWNER/REPO --verify-tag --draft --title "星匣 vVERSION" --notes-file release-notes.md FILES...
```

4. 检查附件名、字节数和下载后的哈希；通过后发布 release。**先让附件可下载，再切换在线清单**。
5. 把已验证 `stable.candidate.json` 作为仓库 `updates/stable.json` 推送。旧清单应保持到新附件就绪，避免用户检查到不可下载的新版本。
6. 首次启用前设置 `src/native.js` 中 `UPDATE_PUBLISHED=true`，与正确地址一起编进本次新包；本地测设置界面和原生更新状态，再发布。已经交付的 false 原型需要手动安装首次启用版本；远端清单不会神奇启用旧包按钮。
7. 发布后从**远端**读回 raw 清单，验证 RSA、app、version，再分别下载两个远端附件并验证 size/hash。不能只用本地文件证明发布成功。保留实际校验结果，避免覆盖同 tag 的已发布产物；修复使用新版本号。

GitHub Pages 可选，仅作下载说明页或以后插件的静态托管；**EXE / APK 二进制放 Releases，签名清单放代码仓库 raw 地址**。星匣当前没有需要沿用的枭熊 manifest。不要把 GitHub 的仓库网页地址当成本地应用或插件的可执行资源地址。

## 中国网络与镜像验证

当前引擎候选前缀：gh-proxy.org、ghfast.top、ghproxy.net、GitHub 直连。它们是可变的第三方线路，不能保证全国所有网络可达。检查时并发验证清单，下载失败轮换，仍须验证签名与哈希；不能为解决镜像故障关闭验证。

每次发布若承诺国内可用，应在可用网络上分别测清单和附件真实 GET，记录时间、结果与来源；还需用户网络/实体手机实测。只有 HTTP200 不足以证明拿到安装包，镜像可能返回 HTML。线路变更同步维护两端列表与 UI 下拉选项，不写死“永久可用”。

## 官方参考

- [GitHub CLI release create](https://cli.github.com/manual/gh_release_create)：草稿、附件、verify-tag、notes-file。
- [GitHub Pages 建站](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site)：静态说明页可选。

以上文档于 2026-10-19 查阅。执行新发布前确认实际 CLI/官方接口和仓库状态。

本项目已有 tools/publish-github.py --publish --essential-only：只发布原生更新 ZIP（也可首次安装）、APK、HTML、源码和校验文件，适合 GitHub Actions 排队或完整运行环境包上传过慢时使用。仍须上传完整附件、公开 GET 读回 SHA256 后再切换 stable.json。不能把未完成的 Full/Light 云端组装说成已发布。tests/online-windows.py 使用实际 C# 引擎；tests/online-android.cjs 在独占 emulator-5590 的只读模拟器内执行真实签名 APK 更新并检查资料保留，不操作实体手机。生产 APK 不开放调试，用系统界面验证；安装完成应先结束安装器，待包就绪再重启应用。
