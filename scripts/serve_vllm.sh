#!/usr/bin/env bash
# 启动 vLLM OpenAI 兼容服务（GLM-5.3-Flash，glm47 解析器）
# 依赖: vLLM >= 0.29.0, FlashInfer >= 0.6.17
set -euo pipefail

MODEL_PATH="${MODEL_PATH:?请先设置 MODEL_PATH 指向权重目录}"
TP="${TENSOR_PARALLEL_SIZE:-8}"
PORT="${PORT:-8000}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-131072}"
GPU_MEM_UTIL="${GPU_MEMORY_UTILIZATION:-0.92}"
SERVED_NAME="${SERVED_MODEL_NAME:-glm-5.3-flash}"
EXTRA_ARGS="${EXTRA_ARGS:-}"
LOG="${LOG_FILE:-$PWD/vllm-server.log}"

echo "==> vLLM 启动参数:"
echo "    model=$MODEL_PATH tp=$TP port=$PORT max_model_len=$MAX_MODEL_LEN gpu_mem=$GPU_MEM_UTIL"

nohup vllm serve "$MODEL_PATH" \
  --served-model-name "$SERVED_NAME" \
  --tensor-parallel-size "$TP" \
  --max-model-len "$MAX_MODEL_LEN" \
  --gpu-memory-utilization "$GPU_MEM_UTIL" \
  --tool-call-parser glm47 \
  --reasoning-parser glm47 \
  --enable-auto-tool-choice \
  --disable-log-requests \
  $EXTRA_ARGS >"$LOG" 2>&1 &

echo $! > vllm-server.pid
echo "==> vLLM 启动中 (PID $(cat vllm-server.pid))，日志: $LOG"
echo "==> 大模型加载耗时较长（772GB 权重），请耐心等待；用 scripts/smoke_test.sh 探活。"
