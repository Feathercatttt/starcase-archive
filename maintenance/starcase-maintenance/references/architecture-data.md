# 结构与数据

## 代码定位

| 路径 | 职责 |
| --- | --- |
| `src/index.html` / `style.css` | 桌面索引与阅读页、手机导航、对话框、视觉样式 |
| `src/templates.js` | 19 个标准模板、字段分组、表格行列定义、初始示例 |
| `src/model.js` | 格式验证、合并、搜索、导出、IndexedDB、本机服务保存与冲突处理 |
| `src/app.js` | 阅读、分组编辑、灵感转条目、图片、自定义字段、关联和导入预览 |
| `src/native.js` | Windows / Android 桥接、文件导出、更新 UI 和原生互通回调 |
| `src/transfer.js` | 选中条目分发、二维码、方向选择、接收预览 |
| `native/server.py` | 本机 JSON、版本化 API、局域网临时分享、自动备份 |
| `native/windows/Program.cs` | EXE 窗口、WebView2、进程生命周期、原生消息 |
| `native/android/src/com/starcase/archive/` | APK WebView、相机 ZXing、LAN 传输、更新与文件保存 |

## 持久格式与身份

普通互通包是 UTF-8 JSON：

```json
{"format":"starcase-archive","packageVersion":1,"kind":"collection","data":{"app":"starcase-archive","schemaVersion":1,"id":"stable-library-id","title":"我的档案","entries":[],"projects":[],"media":[]}}
```

条目重要键：`id/templateId/kind/area/system/title/summary/tags/aliases/projectId/status/favorite/fields/customFields/relations/source/coverId/createdAt/updatedAt`。

- `fields` 使用模板稳定键，数值允许保留公式原文。当前编辑器不是自动执行公式的角色卡。
- `customFields` 含稳定 `id`、`key`、`label`、`type`、`value`。类型为 text / long / number / boolean / list。
- 表格行也有稳定 `id`，不能用行号作永久关联。
- `relations.targetId` 关联条目 ID，关联不随标题变化断开。
- `source` 含 `kind/title/url/revision/retrievedAt/raw/review`。原文逐字保留；映射字段可改，`review` 为 pending 或 checked。
- `attachments` 为可选数组，行含 `mediaId/name/sourceToken`，引用同一库中的图片。阅读页折叠显示；单条分发收集 coverId 与全部 attachments，导入碰到图片 ID 冲突时两处一起重映射。全库备份保留所有 media，包括暂未被引用的原图。
- `media` 保存原始 PNG / JPEG / WebP / GIF data URL；`coverId` 引用图片。不把 SVG 或远端脚本放进原生页面。
- 空值表示未提供，不推定 0；原文明确的 `—` 按字面保留。
- 未识别的 `fields` 保留并可在“其它导入字段”编辑；新增字段不能在导入导出中悄悄丢失。

权威定义在 `src/templates.js`，生成 `outputs/标准模板.json`、`资料包-schema.json` 和 `数据结构说明.json`。JSON Schema 不能替代应用验证、资源大小限制和来源校对。

`window.ArchiveApp` 暴露 snapshot / templates / package / exportStructured / validate 供检查。编辑先留草稿，保存才提交；转换灵感仅在正式条目保存后改变原灵感状态。

## 分区和模板

- ideas：灵感。
- world：地点、NPC、势力、植物、设定历史、自由条目。
- modules：COC 模组总览、场景、线索、NPC、时间线、线索道具、结局，及自由条目。
- rules：通用私设规则、DND 魔法物品 / 怪物、COC 物品 / 怪异，及自由条目。

DND 怪物字段参考用户私设模板，普通怪物不必填写传奇/Boss 组。COC 模板先提供创作骨架，不补造用户尚未给出的规则。

## 保存、同步和外部整理

Windows：`%LOCALAPPDATA%/StarcaseArchive/library.json`，包装为 `{revision,data,updatedAt}`，同目录 `backups` 只保留最近 10 份。页面和 APK 的数据库名均为 `starcase-archive-v1`，但按设备与来源独立保存。Android 来源固定 `https://starcase.local/`，改来源会导致看似丢数据。

服务 `http://localhost:17652`：

- GET `/api/session`：本机连接信息。不要把返回的 token 打印给用户或写进公开材料。
- GET `/api/guide`：接口说明。
- GET `/api/templates`、`/api/schema`：实际安装版本的模板与资料包定义。
- GET `/api/archive?since=N`：带 revision 的资料。
- GET `/api/entry/ID`：单条。
- POST `/api/entries/upsert`：`{revision,entries:[部分或完整条目]}`，合并字段，保留其它条目。并发版本错误返回 409，需重新读取再处理。
- POST `/api/archive`：完整 CAS 保存，仅在确实需要整库替换或合并时用。

除 session 外认证头为 `X-Starcase-Token`，从本机 `connection.json` 读取。若应用正在打开，优先用 API；不要绕过版本锁直接写 library.json。页面约三秒读取外部变化，未提交本地修改会阻止直接覆盖，设置中可处理冲突。

扫码是同局域网临时交换，不是云端持续同步：电脑显码、APK 调相机扫描；可手机接收电脑或手机发送所选资料，接收后预览确认。LAN 端口 17653、路径 `/a/随机令牌/`、20 分钟到期，关闭分享后失效。普通文件也可双向互通。单包 32 MB、单张图片 8 MB，较大库分批选取。

Java / JS 分块按 UTF-16 字符长度协同，不能截断代理对。`readLanChunk16` 末尾若为高代理会缩短，JS 应按实际返回字符串长度推进 offset，勿固定加 48000。

## 飞书整理

使用可用的 `lark-doc` / `lark-wiki` 技能和 `--as user`。先取当前原文与 revision，再映射字段；保留 raw、URL、读取时间与 pending 状态。以 `ok:true` 和实际读回为凭据，目录浅层枚举不能证明条目缺失。

本机 `private/feishu/` 是私有缓存，`private/make-feishu-sample.py` 生成独立导入包。v0.1.0 仅试取易伤与抵抗、第六发魔弹、水灵-狮、雾隐草四篇和一张原始物品图。完整私设尚未批量迁移。样本单独交给用户，不装进公开源码或更新包。

批量迁移只处理用户明确指定的目录。先递归读完当前分支（不限页），保留节点路径、原文与修订号，再逐项映射。当前私有脚本在 `private/migrate-feishu.py`、`build-monster-import.py`、`install-monster-import.py`；这些含个人来源定位信息，不进入公开源码。多阶段文档可拆成关联形态卡，主卡复用原 URL 的 UUIDv5，其他形态使用稳定后缀；每张卡仍保留完整 source.raw 和该形态 partRaw。

六维值以原文口径记录，用 statBasis / 可编辑说明注明调整值或原样数值；等级与熟练加值分开，缺失值留空。遇到面板与备注冲突时保留两处、标待校对，不擅自选裁定。图片按内容 SHA256 去重，附件保留原 file token 与名称。导入前独立备份，读本机版本后 CAS 合并；原样本仅在用户内容未改时补全，其他已有资料保留。最后对实际 API 读回、原文逐字、所有附件引用、桌面及手机宽度和选中导出往返进行核对。个人资料包仍只放 outputs/private，不放安装包或 GitHub。

用户在本次飞书迁移中明确修正：怪物图鉴资料放在“世界观 → 人物”。此批条目使用 area=world、kind=npc，同时保留 dnd.monster.v1 模板及完整怪物字段，系列目录使用世界观设定条目。不要因模板默认区为 rules 而把这批人物搬回规则区；移动应只改导航分类，保留 ID、fields、source 和关系，避免重复导入。
