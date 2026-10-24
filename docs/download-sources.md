# 权重下载源说明

同一份 GLM-5.3-Flash 权重在多个平台有镜像。按自动化程度排序：

## 1. HuggingFace（工作流默认，推荐）

```bash
# huggingface_hub CLI（脚本已自动安装）
export HF_ENDPOINT=https://hf-mirror.com   # 国内加速；海外用 https://huggingface.co
export HF_HUB_ENABLE_HF_TRANSFER=1          # 多线程下载
hf download zai-org/GLM-5.3-Flash-BF16 --local-dir ~/glm-models/zai-org__GLM-5.3-Flash-BF16
```

- 仓库：<https://huggingface.co/zai-org/GLM-5.3-Flash-BF16>
- 支持断点续传；gated 仓库需 `HF_TOKEN`（在仓库 Secrets 中配置 `HF_TOKEN`）。

## 2. ModelScope（国内备选）

```bash
pip install modelscope
modelscope download --model zai-org/GLM-5.3-Flash-BF16 \
  --local_dir ~/glm-models/zai-org__GLM-5.3-Flash-BF16
```

- 页面：<https://modelscope.cn/models/zai-org/GLM-5.3-Flash-BF16>

## 3. GitCode AI 社区（用户指定来源）

模型页：<https://ai.gitcode.com/zai-org/GLM-5.3-Flash-BF16>

GitCode AI 社区（AtomGit AI 社区）目前**未开放公开的模型文件 API**：
直接请求文件地址会返回 302/429（WAF），`.git` 端点会跳转到 AtomGit 首页。
可用的两种方式：

### A. manifest 直链模式（半自动，推荐）

1. 浏览器登录 <https://ai.gitcode.com>，打开模型页 → 文件列表。
2. 对每个文件复制下载直链（DevTools → Network 中找到的 `fileHost` 地址），
   逐行写入仓库根目录的 `gitcode-urls.txt`（不要提交到 Git，已在 `.gitignore`）。
3. 执行：
   ```bash
   SOURCE=gitcode MODEL_ROOT=~/glm-models bash scripts/download_model.sh
   ```
   脚本会优先用 `aria2c`（`-x8 -s8` 多连接 + 断点续传），无 aria2c 时退化为 `wget -c`。

### B. 登录态 Cookie 模式（实验性）

```bash
# 浏览器 DevTools → Application/存储 → Cookies → ai.gitcode.com，复制整串 Cookie
export GITCODE_COOKIE='<粘贴完整 Cookie>'
SOURCE=gitcode bash scripts/download_model.sh
```

> 注意：GitCode WAF 对频繁请求会返回 429。若被限流，请间隔重试或改用 HF/ModelScope 镜像。
> Cookie 含账户凭证，**切勿写入仓库或日志**。

## 4. 本地已就绪（local）

```bash
# 自行准备权重到 $MODEL_ROOT/zai-org__GLM-5.3-Flash-BF16 后：
SOURCE=local MODEL_ROOT=/data/glm-models bash scripts/download_model.sh
```

## 目录命名约定

`download_model.sh` 统一将权重落到：

```
$MODEL_ROOT/<owner>__<name>/
  ├── config.json
  ├── tokenizer_config.json / tokenizer.json / *.tiktoken 等
  ├── *.safetensors（多分片）
  └── （多模态）preprocessor_config.json 等
```

Docker Compose 通过 `MODEL_DIR_NAME` 环境变量映射到容器内 `/models/<owner>__<name>`。
