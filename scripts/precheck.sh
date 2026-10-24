#!/usr/bin/env bash
# 硬件与磁盘预检：BF16 权重约 772GB，FP8 约 386GB（含约 15% KV/运行时余量）
set -euo pipefail

PRECISION="${PRECISION:-bf16}"
TP="${TENSOR_PARALLEL_SIZE:-8}"
MODEL_ROOT="${MODEL_ROOT:-$HOME/glm-models}"

case "$PRECISION" in
  bf16) WEIGHTS_GB=772 ;;
  fp8)  WEIGHTS_GB=386 ;;
  *)    echo "::error::未知精度: $PRECISION (支持 bf16/fp8)"; exit 2 ;;
esac

echo "==> 精度: $PRECISION | 权重约 ${WEIGHTS_GB} GB | 期望 GPU 数: $TP"
FAIL=0

# ---- GPU 检查 ----
if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "::error::未检测到 nvidia-smi。本模型需要 NVIDIA GPU（AMD/昇腾方案见 docs/hardware.md）"
  FAIL=1
else
  GPU_COUNT=$(nvidia-smi -L | wc -l)
  VRAM_TOTAL=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits \
               | awk '{s+=$1} END {printf "%d", s/1024}')
  echo "==> GPU: ${GPU_COUNT} 卡 | 合计显存: ${VRAM_TOTAL} GB"
  if [ "$GPU_COUNT" -lt "$TP" ]; then
    echo "::error::GPU 数量(${GPU_COUNT}) 小于 tensor-parallel-size(${TP})"
    FAIL=1
  fi
  NEED_VRAM=$(( WEIGHTS_GB * 115 / 100 ))
  if [ "$VRAM_TOTAL" -lt "$NEED_VRAM" ]; then
    echo "::error::显存不足: 需要约 ${NEED_VRAM} GB（权重 ${WEIGHTS_GB}GB + KV/开销），实际 ${VRAM_TOTAL} GB"
    FAIL=1
  fi
fi

# ---- 磁盘检查 ----
mkdir -p "$MODEL_ROOT" 2>/dev/null || true
AVAIL_GB=$(df -BG "$MODEL_ROOT" 2>/dev/null | awk 'NR==2{gsub("G","",$4); print $4}')
[ -z "$AVAIL_GB" ] && AVAIL_GB=$(df -BG . | awk 'NR==2{gsub("G","",$4); print $4}')
NEED_DISK=$(( WEIGHTS_GB * 130 / 100 ))
echo "==> 磁盘($MODEL_ROOT) 可用: ${AVAIL_GB} GB | 需要 >= ${NEED_DISK} GB（含下载临时空间）"
if [ "$AVAIL_GB" -lt "$NEED_DISK" ]; then
  echo "::error::磁盘空间不足，至少需要 ${NEED_DISK} GB"
  FAIL=1
fi

if [ "$FAIL" -eq 0 ]; then
  echo "==> 预检通过 ✔"
else
  echo "==> 预检未通过 ✘"; exit 1
fi
