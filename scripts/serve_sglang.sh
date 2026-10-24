#!/usr/bin/env bash
# 启动 SGLang OpenAI 兼容服务（GLM-5.3-Flash）
# 依赖: SGLang >= v0.5.20（推荐镜像 lmsysorg/sglang:latest）
set -euo pipefail

MODEL_PATH="${MODEL_PATH:?请先设置 MODEL_PATH 指向权重目录}"
TP="${TENSOR_PARALLEL_SIZE:-8}"
PORT="${PORT:-8000}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-131072}"
SERVED_NAME="${SERVED_MODEL_NAME:-glm-5.3-flash}"
EXTRA_ARGS="${EXTRA_ARGS:-}"
LOG="${LOG_FILE:-$PWD/sglang-server.log}"

echo "==> SGLang 启动参数:"
echo "    model=$MODEL_PATH tp=$TP port=$PORT context=$MAX_MODEL_LEN"

nohup python3 -m sglang.launch_server \
  --model-path "$MODEL_PATH" \
  --served-model-name "$SERVED_NAME" \
  --tp-size "$TP" \
  --host 0.0.0.0 \
  --port "$PORT" \
  --context-length "$MAX_MODEL_LEN" \
  --reasoning-parser glm47 \
  --tool-call-parser glm47 \
  --mem-fraction-static 0.85 \
  $EXTRA_ARGS >"$LOG" 2>&1 &

echo $! > sglang-server.pid
echo "==> SGLang 启动中 (PID $(cat sglang-server.pid))，日志: $LOG"
echo "==> 如遇 MTP/投机解码相关告警，可去掉 --speculative-* 参数或参阅 cookbook.sglang.io。"
