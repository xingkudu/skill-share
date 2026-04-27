# Primark 标签处理 Skill 三件套

为给 **Primark** 供货的工厂/外贸业务量身做的 OpenClaw / Claude Skills。

覆盖从「下单给印刷厂」到「收到打样后核对」的完整闭环：

| Skill | 干什么 | 触发场景 |
|---|---|---|
| **`primark-purchase-order`** | 把 Primark 发来的 `Ticket Request` + `PO` PDF，整合成给国内印刷厂的「价格小圆贴 & 条码贴 采购单 .xls」 | 收到客户 PO 后，需要给印刷厂下单 |
| **`primark-ticket-check`** | 比对印刷厂打回的**条码贴/价签 PDF** 与原始 Ticket Request，强校验 SKU / ORIN / Kimball / 条码 / 颜色 / 尺码 / 价格 / 币种 / 供应商号 | 工厂打样回来，反核合格再放量产 |
| **`primark-care-label-check`** | 比对印刷厂打回的**洗标 PDF** 与「洗标采购单 .xls」+「洗标-模版 .pdf」，校验内容字段、欧洲单/美国单版面、阿拉伯文 RTL、批次分页与张数标注 | 洗标打样回来，反核合格再放量产 |

## 关键业务知识（已硬编码在 skill 内）

> 🎯 **Ticket 数量 = PO 数量 × 1.02**（Primark 统一 +2% 损耗）
>
> - **PO 数量** 才是权威订单量 → 下采购单、报关都以 PO 为准
> - **Ticket 数量** 仅是 Primark 准备贴纸时多画的余量
> - 工厂打回的条码贴数量与 Ticket 不等不要报错，**与采购单（=PO 数）一致即可**

---

## 🚀 安装

> ⚠️ 把下面所有命令里的 `<owner>` 换成本仓库实际所在的 GitHub 账号/组织名。

### 方式 ① — ClawHub 一键装（最丝滑，**推荐 OpenClaw 用户**）

> 前提：维护者已把这三个 skill 上架到 [clawhub.ai](https://clawhub.ai)。

```bash
openclaw skills install primark-purchase-order
openclaw skills install primark-ticket-check
openclaw skills install primark-care-label-check
```

升级：

```bash
openclaw skills update --all
```

### 方式 ② — `curl` 一键脚本（任意 AI agent 通用）

把整个仓库的三个 skill 拉到当前 agent 的 `skills/` 目录：

```bash
# 默认装到 OpenClaw 当前 agent workspace
cd "$(openclaw config get workspace.dir 2>/dev/null || echo ~/.openclaw/workspace/agents/$(openclaw status --json 2>/dev/null | jq -r .activeAgent))" \
  && mkdir -p skills && cd skills \
  && curl -L https://github.com/<owner>/skill-share/archive/refs/heads/main.tar.gz \
     | tar xz --strip-components=1 --wildcards '*/primark-*'
```

或安装到 OpenClaw 全局 `~/.openclaw/skills/`（所有 agent 都能用）：

```bash
mkdir -p ~/.openclaw/skills && cd ~/.openclaw/skills \
  && curl -L https://github.com/<owner>/skill-share/archive/refs/heads/main.tar.gz \
     | tar xz --strip-components=1 --wildcards '*/primark-*'
```

### 方式 ③ — `git clone`（想跟踪上游更新）

```bash
git clone https://github.com/<owner>/skill-share.git ~/skill-share
ln -s ~/skill-share/primark-purchase-order   ~/.openclaw/skills/primark-purchase-order
ln -s ~/skill-share/primark-ticket-check     ~/.openclaw/skills/primark-ticket-check
ln -s ~/skill-share/primark-care-label-check ~/.openclaw/skills/primark-care-label-check
# 之后随时 cd ~/skill-share && git pull 即可同步更新
```

### 方式 ④ — 手动复制（Claude Code / Codex / Cursor 等其他主体）

任何 ACP 主体只要支持 "skills 目录"约定，把 SKILL.md 所在文件夹丢进去即可：

```bash
cp -R primark-* /path/to/your-agent/skills/
# Claude Code: ~/.claude/skills/   或   <project>/.claude/skills/
# Codex / Cursor / 自建 agent: 各自的 skills 目录
```

启动新会话后即可被自动发现。

---

## 🔧 Workspace 路径约定

三个 skill 内的 Python 落盘代码都通过下列规则解析 workspace 根目录，**不依赖任何用户名/绝对路径**：

```python
ws = pathlib.Path(os.environ.get("OPENCLAW_WORKSPACE_DIR") or os.getcwd()).resolve()
```

- OpenClaw 会自动注入 `OPENCLAW_WORKSPACE_DIR`
- 其他主体在 agent workspace 目录下启动即可，会落到当前 cwd

输出统一落到：`<workspace>/projects/Primark/<款号或PO号>/`

---

## 📁 文件清单

```
primark-purchase-order/
├── SKILL.md
└── reference/                # 各类标签实物参照图
    ├── 条码贴.png
    ├── 价格小圆贴1.png
    ├── 价格小圆贴2.png
    └── baby小圆贴.png

primark-ticket-check/
└── SKILL.md

primark-care-label-check/
├── SKILL.md
└── templates/                # 洗标版面模板
    ├── 洗标-模版.pdf
    ├── template-page1.png
    └── template-page2.png
```

---

## 🛠 给维护者：发布到 ClawHub

详见 [`PUBLISH.md`](./PUBLISH.md)。一句话版本：

```bash
npm i -g clawhub
clawhub login
./scripts/publish-all.sh 1.0.0 "Initial release"
```

---

## 🖥️ 系统兼容性

| 平台 | 支持情况 | 备注 |
|---|---|---|
| **macOS** | ✅ 原生 | Intel / Apple Silicon 均可 |
| **Linux** | ✅ 原生 | 任意发行版 |
| **Windows 10/11** | ✅ 原生 | skill Python 代码纯跨平台 |
| **Windows (cmd.exe)** | ⚠️ `publish-all.sh` 跑不了 | 用 PowerShell 版 `publish-all.ps1`，或装 [Git for Windows](https://git-scm.com/download/win) 后用 Git Bash |
| **Windows (PowerShell)** | ✅ | `\.\scripts\publish-all.ps1 -Version 1.0.0 -Changelog "..."` |
| **Windows (WSL)** | ✅ | 与 Linux 一致 |

**Python 依赖**：skill 内仅用 `xlwt` + `Pillow` + 标准库，三平台都有。原本一处 macOS 专属的 `sips` 命令已被改成默认走纯 Python(Pillow)路径，sips 仅作为 macOS 可选加速。

**文件名含中文**：reference 图片和洗标模板文件名是中文。Windows NTFS 没问题；git 如果显示乱码，设一下：

```bash
git config --global core.quotepath false
git config --global i18n.logOutputEncoding utf-8
```

仓库带了 `.gitattributes`，在 Windows checkout 不会把 `.sh`/`.py` 变成 CRLF，二进制文件也不会被误伤。

---

## 📜 License

[MIT](./LICENSE)。第三方 Primark 商标声明详见 LICENSE 末尾。

— 由织语 Tessa（外贸纺织品行业 OpenClaw agent）整理
