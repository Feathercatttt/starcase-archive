# 星匣交接

这是星匣的独立项目，不是旅人手札的下一版。用户当前要求：先交付小而可用的个人资料库，再由另一个 agent 修改小功能。

维护此项目时读取 `maintenance/starcase-maintenance/SKILL.md`。本机已安装副本位于 `C:/Users/PC/.codex/skills/starcase-maintenance/SKILL.md`；项目内版本是可随源码交接的版本。

入口：`src/` 是界面与数据逻辑，`native/` 是 Windows / Android 外壳和本机服务，`tools/` 是构建与本地发布准备。修改源文件后重新生成输出，勿只修改 `outputs/星匣.html`。

`private/`、`.build/`、本机资料目录和签名密钥不进入源码、GitHub 或公开安装包。v0.1.1 配置了独立仓库 `Feathercatttt/starcase-archive`；线上发布要核对远端附件和签名清单，不能只凭本地候选文件宣称完成。

发布准备命令及验证范围见维护 skill。代码修改不意味着可以覆盖用户实际资料。
