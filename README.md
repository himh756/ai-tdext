# ai-tdext · GLM-5.3-Flash-BF16 部署工程

本仓库是 **GLM-5.3-Flash-BF16**（智谱 Z.ai 开源，320B 总参 / 18B 激活，原生多模态 MoE）的本地部署工程：
通过 **GitHub Actions 工作流** + Docker 完成「硬件预检 → 下载权重 → 启动 OpenAI 兼容推理服务 → 冒烟测试 → 保活」的全流程自动化。

> **权重（BF16 约 772 GB）不纳入 Git 仓库**，运行时按需从模型托管平台拉取。
> 本仓库代码以 MIT 许可发布；模型权重遵循 GLM-5.3 License，详见 [NOTICE.md](NOTICE.md)。
> 模型来源参考：[ai.gitcode.com/zai-org/GLM-5.3-Flash-BF16](https://ai.gitcode.com/zai-org/GLM-5.3-Flash-BF16)

## 模型速览

| 项 | 值 |
|----|----|
| 模型 ID | `zai-org/GLM-5.3-Flash-BF16` |
| 架构 | MoE（320B 总参 / 18B 激活），MLA + DSA 稀疏注意力 + KDA 线性注意力混合架构，mHC，原生 MTP |
| 上下文 | 1,048,576 tokens（按显存裁剪，见 `max_model_len`） |
| 模态 | 文本 / 图像 / 视频 |
| 权重体积 | BF16 ≈ 772 GB ｜ FP8 ≈ 386 GB ｜ NVFP4 ≈ 229 GB |
| 推理框架 | vLLM ≥ 0.29.0（需 FlashInfer ≥ 0.6.17）或 SGLang ≥ v0.5.20 |
| 思考预算 | `reasoning_effort`：`low` / `high` / `max`（默认 `max`） |

## 硬件要求（硬约束）

| 精度 | 权重体积 | 最低配置 | 推荐配置 |
|------|----------|----------|----------|
| BF16 | ~772 GB | 8×H200(141G) 或 6×B200(180G) | 8×H200 + NVMe 本地盘 |
| FP8 | ~386 GB | 4×H200 或 2×B200 | 8×H200 |
| NVFP4 | ~229 GB | 2×B200(180G) | 4×B200 |

GitHub **托管 Runner**（最大 64 vCPU / 256 GB 内存，磁盘仅百 GB 级）无法承载本模型，
因此部署工作流默认运行在 **自托管 Runner**（`self-hosted, linux, glm-flash`）上——
这正是"用工作流在自己的机器上运行模型"的标准方式。硬件细节见 [docs/hardware.md](docs/hardware.md)。

## 快速开始

### 方式一：GitHub Actions 工作流（推荐）

1. 在目标机器上注册自托管 Runner 并打标签（任选其一）：

   ```bash
   # 仓库页 → Settings → Actions → Runners → New self-hosted runner，按指引执行，并添加标签：
   ./config.sh --url https://github.com/himh756/ai-tdext --token <TOKEN> --labels glm-flash --unattended
   # 或编辑 ~/actions-runner/.runner 后重启，确保标签为 self-hosted,linux,glm-flash
   ```

2. 仓库页 → **Actions → Deploy GLM-5.3-Flash (BF16) → Run workflow**，按需填写输入：

   | 输入 | 默认 | 说明 |
   |------|------|------|
   | `framework` | `vllm` | 推理框架：`vllm` / `sglang` |
   | `precision` | `bf16` | 权重精度：`bf16` / `fp8` |
   | `source` | `huggingface` | 权重来源：`huggingface`（hf-mirror 加速）/ `modelscope` / `gitcode` / `local` |
   | `model_id` | `zai-org/GLM-5.3-Flash-BF16` | 模型 ID，可按精度覆盖 |
   | `hf_endpoint` | `https://hf-mirror.com` | HF 端点，海外可改 `https://huggingface.co` |
   | `tensor_parallel_size` | `8` | 张量并行 GPU 数 |
   | `port` | `8000` | 服务端口 |
   | `max_model_len` | `131072` | 最大上下文（1M 需极大 KV，按显存量力而行） |
   | `smoke_test` | `true` | 启动后是否执行推理冒烟测试 |
   | `keep_alive_minutes` | `120` | 服务保活时长（分钟），到点回收 |

3. 工作流自动完成：预检 → 下载（断点续传）→ 启动服务 → 冒烟测试 → 保活 → 回收并上传日志。
   服务为 OpenAI 兼容 API：`http://<runner-ip>:8000/v1/chat/completions`。

> 为什么默认 `source=huggingface`：GitCode AI 社区对程序化下载限制较多（需登录态、WAF 限流）。
> 同一份权重在 HuggingFace / ModelScope 有镜像，可用 CLI 断点续传；GitCode 手动下载通道见
> [docs/download-sources.md](docs/download-sources.md)。

### 方式二：Docker Compose

```bash
# 1. 先下载权重（任选其一）
MODEL_ROOT=~/glm-models bash scripts/download_model.sh   # 默认 HF 镜像源

# 2. 启动（GPU 需可见：nvidia-container-toolkit）
MODEL_ROOT=~/glm-models TENSOR_PARALLEL_SIZE=8 docker compose -f docker/docker-compose.yml up -d

# 3. 验证
bash scripts/smoke_test.sh
```

### 方式三：裸机脚本

```bash
export MODEL_ROOT=~/glm-models
bash scripts/precheck.sh                      # 硬件/磁盘预检
bash scripts/download_model.sh                # 下载权重
bash scripts/serve_vllm.sh &                  # 或 serve_sglang.sh
bash scripts/smoke_test.sh                    # 健康检查 + 推理测试
```

## 调用示例

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "glm-5.3-flash",
    "messages": [{"role": "user", "content": "用一句话介绍 GLM-5.3-Flash"}],
    "max_tokens": 512,
    "chat_template_kwargs": {"reasoning_effort": "low", "clear_thinking": true}
  }'
```

- `reasoning_effort`：`low` / `high` / `max`（默认 `max`，思考最深、最贵）
- `clear_thinking`：多轮对话场景传 `true`（清空上一轮思维链）
- 多模态：`content` 数组中加入 `{"type": "image_url", "image_url": {"url": "..."}}`

## 目录结构

```
├── .github/workflows/
│   ├── deploy-glm-flash.yml   # 主部署工作流（手动触发，自托管 Runner）
│   └── ci.yml                 # 推送/PR 时校验 YAML 与 Shell 语法
├── scripts/
│   ├── precheck.sh            # 硬件/磁盘/显存预检（BF16≈772GB，FP8≈386GB）
│   ├── download_model.sh      # 多源权重下载（HF/ModelScope/GitCode/本地）
│   ├── download_gitcode.sh    # GitCode 通道（manifest 直链 + 登录态说明）
│   ├── serve_vllm.sh          # vLLM 启动（glm47 解析器）
│   ├── serve_sglang.sh        # SGLang 启动
│   └── smoke_test.sh          # 健康检查 + 推理冒烟测试
├── configs/                   # 环境变量样例（vllm / sglang）
├── docker/                    # Dockerfile + docker-compose
└── docs/                      # 硬件需求、下载源说明
```

## 常见问题

- **显存不够**：BF16 需 ~772GB 权重。降级顺序：BF16 → FP8（386GB）→ NVFP4（229GB，需 Blackwell）；
  或缩短 `max_model_len` 降低 KV 占用；或用 KTransformers 做 CPU offload（速度大幅下降）。
- **下载慢/失败**：国内用 `hf_endpoint=https://hf-mirror.com` 或 `source=modelscope`；
  HF 下载默认开启 `hf_transfer` 多线程。
- **工作流抢不到 GPU**：工作流内置 `concurrency` 串行执行；请确保 Runner 独占或已隔离 GPU。
