#!/usr/bin/env bash
# 健康检查 + 推理冒烟测试
set -euo pipefail

PORT="${PORT:-8000}"
MODEL="${SERVED_MODEL_NAME:-glm-5.3-flash}"
BASE="http://127.0.0.1:${PORT}"
TIMEOUT="${SMOKE_TIMEOUT_S:-7200}" # 大权重加载可能超过 1 小时

echo "==> 等待服务就绪（最多 ${TIMEOUT}s）..."
START=$(date +%s)
until curl -sf "$BASE/health" >/dev/null 2>&1; do
  NOW=$(date +%s)
  if [ $((NOW - START)) -ge "$TIMEOUT" ]; then
    echo "::error::服务未在 ${TIMEOUT}s 内就绪，请查看 vllm-server.log / sglang-server.log"
    exit 1
  fi
  sleep 15
done
echo "==> 服务就绪 ✔ 耗时 $(( $(date +%s) - START ))s"

echo "==> 发送测试请求（reasoning_effort=low 以缩短耗时）..."
RESP=$(curl -sf "$BASE/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"$MODEL\",
    \"messages\": [{\"role\": \"user\", \"content\": \"用一句话介绍你自己\"}],
    \"max_tokens\": 256,
    \"chat_template_kwargs\": {\"reasoning_effort\": \"low\", \"clear_thinking\": true}
  }")

echo "$RESP" | python3 -c "
import sys, json
d = json.load(sys.stdin)
msg = d['choices'][0]['message']
print('模型回复:', (msg.get('content') or '')[:300])
print('Token 用量:', d.get('usage'))
"
echo "==> 冒烟测试通过 ✔"
