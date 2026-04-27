#!/usr/bin/env bash
# 一键发布全部 Primark skill 到 ClawHub。
#
# 用法：
#   ./scripts/publish-all.sh <version> "<changelog>"
#
# 例：
#   ./scripts/publish-all.sh 1.0.0 "Initial release"
#   ./scripts/publish-all.sh 1.0.1 "Fix care-label RTL detection"

set -euo pipefail

VERSION="${1:-}"
CHANGELOG="${2:-}"

if [[ -z "$VERSION" ]]; then
  echo "❌ 缺少版本号参数。用法：$0 <semver> \"<changelog>\""
  exit 1
fi

if ! command -v clawhub >/dev/null 2>&1; then
  echo "❌ 找不到 clawhub CLI。先装一下：npm i -g clawhub"
  exit 1
fi

# 登录态检查
if ! clawhub whoami >/dev/null 2>&1; then
  echo "❌ 未登录 ClawHub。先跑：clawhub login"
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# slug → display name → tags 映射
declare -a SKILLS=(
  "primark-purchase-order|Primark Purchase Order Generator|textile,primark,purchase-order,label,fashion-supply-chain,chinese,latest"
  "primark-ticket-check|Primark Ticket Check|textile,primark,ticket-check,qa,label,fashion-supply-chain,chinese,latest"
  "primark-care-label-check|Primark Care Label Check|textile,primark,care-label,qa,multilingual,fashion-supply-chain,chinese,latest"
)

echo "🚀 准备发布 ${#SKILLS[@]} 个 skill (version=$VERSION) → ClawHub"
echo

for entry in "${SKILLS[@]}"; do
  IFS='|' read -r slug name tags <<< "$entry"
  echo "── $slug ──"
  if [[ ! -d "$slug" ]]; then
    echo "  ⚠️  目录不存在，跳过：$slug"
    continue
  fi
  clawhub skill publish "./$slug" \
    --slug "$slug" \
    --name "$name" \
    --version "$VERSION" \
    --changelog "$CHANGELOG" \
    --tags "$tags"
  echo "  ✅ $slug @ $VERSION 已上架"
  echo
done

echo "🎉 全部完成。查看：https://clawhub.ai/skills?q=primark"
