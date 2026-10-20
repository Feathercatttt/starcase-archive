# 构建与验证

以下路径是 2026-10-19 的已验证环境，后续先核实依赖存在。所有命令在 `D:/软件/DSH 大肥鱼专用/星匣` 执行。

## 本地构建

```powershell
python -X utf8 tools/build-web.py
python -X utf8 tools/build-native.py windows
python -X utf8 tools/build-native.py android
python -X utf8 tools/package-release.py --full
```

web 构建把 src 合成单文件 `outputs/星匣.html`，同时生成模板定义。不能只改生成 HTML。Windows 输出 `outputs/星匣-Windows/星匣.exe`，APK 为 `outputs/星匣-Android.apk`。

构建依赖暂时从 `C:/Users/PC/Documents/Codex/2026-10-13/new-chat` 的 `work` 目录复用；这只是 SDK / 运行库来源，不修改旅人手札。原生构建可设置 `STARCASE_BUILD_TOOLS` 指到等价依赖根目录：

- `work/windows-deps/python`：嵌入式 Python。
- `work/windows-deps/lib/net462`、`build/native/x64`：WebView2。
- `work/windows-deps/WebView2Installer/MicrosoftEdgeWebView2RuntimeInstallerX64-complete.exe` 与 `work/v16-runtime-info.json`：原始离线安装器及哈希。
- 项目自有 `native/windows/app.manifest`：asInvoker 与 Windows DPI manifest，不再从旧项目覆盖。
- `work/android-sdk`：SDK，build-tools 36.0.0、android-36。
- `work/android-deps/zxing-core-3.5.3.jar` 与对应许可。
- Java `C:/Program Files/Microsoft/jdk-21.0.10.7-hotspot`。
- .NET Framework 编译器 `C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe`。

Android aapt2 在此环境不接受中文构建绝对路径，因此脚本把项目暂存到依赖根目录的 ASCII 路径 `work/starcase-build-0.1`，再把 APK 复制回星匣。迁移开发机时可改脚本的依赖定位，不要因此改变应用身份。

`tools/prepare-native.py` 是**首版的一次性移植脚本**，会复制旧引擎并覆盖原生源文件。日常维护禁止把它当成构建步骤；已有签名密钥也不重新生成。

Windows 缺 WebView2 时，完整包内的微软离线安装器供用户安装。轻量包不带此大文件，适合已具备运行环境的电脑。不能声称 WebView2 DLL 等于已内置整个浏览器运行时。

## 验证按改动选用

```powershell
node tests/browser.cjs
node tests/server.cjs
python -X utf8 tests/windows.py
python -X utf8 tools/build-native.py android --qa
node tests/android.cjs
node tests/preview.cjs
```

- browser：离线真实 Edge；12 项交互检查，含保存/取消、连续点击、灵感转换、未知字段、图片、并发保存、导入重复、手机布局与返回。
- server：独立 17952 服务；API CAS、页面轮询、认证、分享失效、预览导入。若本机有私有飞书小样本会额外核对，否则使用公开演示资料。
- windows：实际已构建 EXE / WebView2，`--self-test` 使用正常用户 Temp 目录和端口 17752，不修改真实资料。校验父进程和应用都没有管理员提权；`--archive outputs/星匣-Windows-轻量-v0.1.0.zip` 可验证全新解压。
- android：Android 15 模拟器，实际 Java LAN 双向传输、长中文与 emoji、相机权限与返回、正式 APK 覆盖安装资料保留。**没有实体手机对电脑二维码的识别验收**。
- preview：生成干净桌面/390px 手机预览。browser 测试会覆盖同名预览，最后重新执行 preview。

测试报告写 `tests/*-report.json`；失败诊断写 `.build` 或 `*-failure.json`。先看具体断言与截图，避免通过删检查掩盖产品问题。UI Automator 某些 WebView 不暴露 placeholder，不代表资料没保存；持久性检查读取真实条目和安装结果。

Android 测试只使用 `emulator-5590`，`-read-only` 启动已有 AVD，CDP 转发 19229，桌面测试服务临时占 17652 / 17653；若真实星匣正在运行会拒绝测试。**不要让 adb 自动选择 USB 手机**。仅操作测试自建进程和 -s 明确的模拟器。

`--qa` 生成 `.build/Starcase-QA.apk`，debuggable 且同包名/同签名，仅供隔离模拟器测试；交付和更新附件必须用 `outputs/星匣-Android.apk`。原生测试在 Windows x64 + 这台 Android 模拟器通过，不等于其它系统、实体手机或线上更新安装通过。

## 非管理员启动修复（已复现，2026-10-19）

本机构建目录继承了 Low integrity 标签，导致新编译 EXE 和复制来的内嵌 Python 都以 Low 启动，不能写 Medium 的用户资料目录。它们能在同样为 Low 的 `.build` 测试目录通过，曾掩盖正常启动失败。实际 traceback 是连接文件写入 PermissionError，不是缺 WebView2。

构建脚本已对**输出中的可执行文件**执行 `icacls FILE /setintegritylevel M`，恢复普通桌面程序级别，包括星匣.exe、StarcaseUpdater.exe、runtime/python.exe 与 pythonw.exe。不提权运行，不降低资料目录权限，不改整个工作区标签。

排错先看 `%LOCALAPPDATA%/StarcaseArchive/startup.log` 和 `service-error.log`。用 `icacls` 检查具体程序文件的 Mandatory Label，普通权限实际运行并写入正常用户目录。若用户给此 EXE 的兼容性勾了 RUNASADMIN，仅在处理该程序启动问题时取消其对应 HKCU Layers 标志并保留其它设置；不能清空其它程序兼容性配置。

ZIP 不保留 NTFS integrity 标签：普通用户解压到正常文件夹得到正常 Medium 标签，解压回特殊 Low 构建目录可能再次继承 Low。做分发验证时全新解压到正常 Temp/下载目录，别只在构建树里测。微软说明：[Mandatory Integrity Control](https://learn.microsoft.com/en-us/windows/win32/secauthz/mandatory-integrity-control)。

## 打包

`tools/package-release.py` 只准备本地文件，永不上传；检查 web / 原生内嵌 HTML 一致和版本一致，生成：

- `星匣-Windows-轻量-vVERSION.zip`，及 `--full` 的完整包。
- `Starcase-Source-vVERSION.zip`，仅允许源码/说明/skill，排除 private、缓存、密钥、QA 输出。
- `outputs/release-vVERSION/` 中固定名更新附件、模板 JSON、校验记录。

`--sign` 另生成本地签名候选清单，见发布参考。打包前确认工作区没有用户资料误放入程序目录。不要将整个项目根目录直接压缩上传。

旧 EXE 正在运行且运行文件被锁住时，不强制结束用户进程：设置 STARCASE_WINDOWS_DIR 为独立新版输出文件夹构建，打包时传 --windows-dir 同一路径。tests/windows.py 支持该环境变量。不要让旧 EXE 配上新 service/version.json 后误称构建完成。新版和旧版共用用户数据目录；提醒用户关闭旧窗口后打开新版。
