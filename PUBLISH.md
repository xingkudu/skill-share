# 发布到 ClawHub

本仓库包含 3 个 skill，发布到 [ClawHub](https://clawhub.ai) 后用户就能用 `openclaw skills install <slug>` 一键安装。

## 前置条件

| 条件 | 说明 |
|---|---|
| **Node.js ≥ 18** | 跑 `clawhub` CLI |
| **GitHub 账号 ≥ 1 周** | ClawHub 反滥用要求 |
| **CLI 安装** | `npm i -g clawhub`（或 `pnpm add -g clawhub`） |
| **登录** | `clawhub login` —— 浏览器走 OAuth；CI 用 `clawhub login --token <api-token>` |

## 一次性发布全部三个 skill

### macOS / Linux / WSL / Git Bash

```bash
# 在仓库根目录
./scripts/publish-all.sh 1.0.0 "Initial release"
```

### Windows PowerShell

```powershell
.\scripts\publish-all.ps1 -Version 1.0.0 -Changelog "Initial release"
```

参数：
- Version：版本号（semver）
- Changelog：changelog 文本

## 单独发布某一个

```bash
clawhub skill publish ./primark-purchase-order \
  --slug primark-purchase-order \
  --name "Primark Purchase Order Generator" \
  --version 1.0.0 \
  --changelog "Initial release" \
  --tags "textile,primark,purchase-order,label,latest"

clawhub skill publish ./primark-ticket-check \
  --slug primark-ticket-check \
  --name "Primark Ticket Check" \
  --version 1.0.0 \
  --changelog "Initial release" \
  --tags "textile,primark,ticket-check,qa,label,latest"

clawhub skill publish ./primark-care-label-check \
  --slug primark-care-label-check \
  --name "Primark Care Label Check" \
  --version 1.0.0 \
  --changelog "Initial release" \
  --tags "textile,primark,care-label,qa,multilingual,latest"
```

## 用 `clawhub sync` 自动批量发布（更省事）

```bash
# 自动扫描 ./skills/* 或当前目录下的 skill 文件夹
clawhub sync \
  --root . \
  --bump patch \
  --changelog "Bug fix" \
  --tags "latest"

# 看看会发啥（不真发）
clawhub sync --root . --dry-run
```

⚠️ `clawhub sync` 默认从当前 workdir 找 `skills/`；本仓库结构是把三个 skill **直接平铺在根目录**，所以必须加 `--root .`。

## 删除/下架

```bash
clawhub delete primark-purchase-order --yes
clawhub undelete primark-purchase-order --yes  # 反悔
```

## 升版本流程

1. 改完 SKILL.md / 模板/脚本
2. 在三个 SKILL.md 顶部 frontmatter 把 `version: x.y.z` 改一下（保持 semver）
3. `git commit && git tag vX.Y.Z && git push --tags`
4. 跑 `./scripts/publish-all.sh X.Y.Z "<changelog>"`

## CI 自动发布（可选）

GitHub Actions 例子（`.github/workflows/publish.yml`）：

```yaml
name: Publish to ClawHub
on:
  push:
    tags: ['v*']
jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: npm i -g clawhub
      - run: clawhub login --token "$CLAWHUB_TOKEN" --no-browser
        env: { CLAWHUB_TOKEN: ${{ secrets.CLAWHUB_TOKEN }} }
      - name: Publish all skills
        run: ./scripts/publish-all.sh "${GITHUB_REF_NAME#v}" "Release ${GITHUB_REF_NAME}"
```

需要在 GitHub repo Settings → Secrets 里加 `CLAWHUB_TOKEN`（来自 `clawhub login` 后的 token，或在 clawhub.ai 用户设置生成 API token）。

## 上架后用户怎么装

```bash
openclaw skills install primark-purchase-order
openclaw skills install primark-ticket-check
openclaw skills install primark-care-label-check
```
