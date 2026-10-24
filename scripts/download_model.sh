#!/usr/bin/env bash
# 多源模型权重下载（断点续传）
#   SOURCE: huggingface | modelscope | gitcode | local
#   MODEL_ID: 如 zai-org/GLM-5.3-Flash-BF16
#   MODEL_ROOT: 权重存放根目录，最终落在 $MODEL_ROOT/<owner>__<name>/
set -euo pipefail

SOURCE="${SOURCE:-huggingface}"
MODEL_ID="${MODEL_ID:-zai-org/GLM-5.3-Flash-BF16}"
MODEL_ROOT="${MODEL_ROOT:-$HOME/glm-models}"
HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"
LOCAL_DIR="$MODEL_ROOT/${MODEL_ID//\//__}"

mkdir -p "$LOCAL_DIR"
echo "==> 来源: $SOURCE | 模型: $MODEL_ID | 目标: $LOCAL_DIR"

case "$SOURCE" in
  huggingface)
    python3 -m pip install -q --upgrade "huggingface_hub[hf_transfer]"
    export HF_ENDPOINT HF_HUB_ENABLE_HF_TRANSFER=1
    hf download "$MODEL_ID" --local-dir "$LOCAL_DIR"
    ;;
  modelscope)
    python3 -m pip install -q --upgrade modelscope
    modelscope download --model "$MODEL_ID" --local_dir "$LOCAL_DIR"
    ;;
  gitcode)
    # GitCode AI 社区需登录态/manifest 直链，见 docs/download-sources.md
    bash "$(dirname "$0")/download_gitcode.sh" "$MODEL_ID" "$LOCAL_DIR"
    ;;
  local)
    echo "==> 使用本地已就绪权重: $LOCAL_DIR"
    ;;
  *)
    echo "::error::未知来源: $SOURCE"; exit 2 ;;
esac

# ---- 完整性校验 ----
MISSING=0
for f in config.json tokenizer_config.json; do
  if [ ! -f "$LOCAL_DIR/$f" ]; then
    echo "::error::缺少 $f"; MISSING=1
  fi
done
if ! ls "$LOCAL_DIR"/*.safetensors >/dev/null 2>&1; then
  echo "::error::未找到任何 .safetensors 权重分片"; MISSING=1
fi
[ "$MISSING" -eq 0 ] || exit 1

TOTAL=$(du -sh "$LOCAL_DIR" | cut -f1)
SHARDS=$(ls "$LOCAL_DIR"/*.safetensors | wc -l)
echo "==> 权重就绪 ✔  $LOCAL_DIR (共 ${TOTAL}, ${SHARDS} 个分片)"
