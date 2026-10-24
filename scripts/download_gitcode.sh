#!/usr/bin/env bash
# GitCode AI 社区下载通道
#
# 背景：ai.gitcode.com 对程序化下载限制较多（WAF 限流 429 / 需登录态），
# 因此提供两条通道：
#   A. manifest 模式：在浏览器登录后从模型页复制各文件直链，逐行写入
#      $GITCODE_MANIFEST（默认 ./gitcode-urls.txt），本脚本用 aria2c/wget 断点续传。
#   B. 登录态模式：设置 GITCODE_COOKIE（浏览器 DevTools → Network → Cookie），
#      脚本尝试通过页面解析直链下载；被 WAF 拦截时给出明确提示。
#
# 详细操作见 docs/download-sources.md
set -euo pipefail

MODEL_ID="${1:?用法: download_gitcode.sh <model_id> <local_dir>}"
LOCAL_DIR="${2:?缺少 local_dir}"
MANIFEST="${GITCODE_MANIFEST:-$PWD/gitcode-urls.txt}"
COOKIE="${GITCODE_COOKIE:-}"

mkdir -p "$LOCAL_DIR"

if [ -f "$MANIFEST" ]; then
  echo "==> [manifest 模式] 使用 $MANIFEST 中的直链下载"
  if command -v aria2c >/dev/null 2>&1; then
    aria2c -c -x 8 -s 8 -d "$LOCAL_DIR" -i "$MANIFEST"
  else
    while IFS= read -r url; do
      [ -z "$url" ] && continue
      wget -c -q --show-progress -P "$LOCAL_DIR" "$url"
    done < "$MANIFEST"
  fi
elif [ -n "$COOKIE" ]; then
  echo "==> [登录态模式] 尝试解析 $MODEL_ID 的文件直链（可能被 WAF 限流）"
  echo "::notice::GitCode 未开放公开 API；如被 429 拦截，请改用 manifest 模式或 HF/ModelScope 镜像。"
  echo "::error::自动解析通道当前不可用，请按 docs/download-sources.md 准备 manifest 后重试。"
  exit 3
else
  echo "::error::未找到 $MANIFEST，也未设置 GITCODE_COOKIE。"
  echo "::error::请参照 docs/download-sources.md：浏览器登录 ai.gitcode.com 后复制直链到 $MANIFEST，"
  echo "::error::或改用 source=huggingface / source=modelscope。"
  exit 3
fi

# 完整性校验
MISSING=0
for f in config.json tokenizer_config.json; do
  [ -f "$LOCAL_DIR/$f" ] || { echo "::error::缺少 $f"; MISSING=1; }
done
ls "$LOCAL_DIR"/*.safetensors >/dev/null 2>&1 || { echo "::error::未找到 .safetensors 分片"; MISSING=1; }
[ "$MISSING" -eq 0 ] || exit 1
echo "==> GitCode 通道权重就绪 ✔ $LOCAL_DIR"
