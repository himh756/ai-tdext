# 硬件需求与部署拓扑

## 权重体积（下载 + 落盘）

| 精度 | 权重体积 | 说明 |
|------|----------|------|
| BF16 | **~772 GB** | `zai-org/GLM-5.3-Flash-BF16`，完整精度，微调/复现基准 |
| FP8 | ~386 GB | `zai-org/GLM-5.3-Flash`，原生 FP8 权重，推理性价比最高 |
| NVFP4 | ~229 GB | 需 NVIDIA Blackwell（B200/GB200 等） |

下载临时空间建议再留 30%（BF16 至少准备 **1 TB 可用磁盘**）。

## GPU 配置（vLLM 官方 recipe）

| 精度 | 最低配置 | 推荐配置 | 备注 |
|------|----------|----------|------|
| BF16 | 8×H200（141GB）或 6×B200（180GB） | 8×H200 | 772GB 权重 + KV cache，4×B200(720GB) 也放不下 |
| FP8 | 4×H200 或 2×B200 | 8×H200 | 386GB 权重 + KV |
| NVFP4 | 2×B200 | 4×B200 | 229GB 权重 |

- KV cache 会进一步挤占显存：上下文从 128K 缩到 32K 可显著降低 KV 占用。
- Hopper（H100/H200）BF16 KV cache；Blackwell 可用 FP8 KV（`--kv-cache-dtype fp8`）。
- 多机：vLLM/SGLang 支持多节点 TP/EP，需 InfiniBand/RoCE；单节点 8 卡即可跑 BF16。

## 其他平台

- **AMD Instinct**：MI300X/MI355X（192-288GB），用 `vllm/vllm-openai-rocm:nightly`，TP=4。
- **华为昇腾**：950PR 8×128GB（vLLM Ascend，单节点 TP=8，FP8）。
- **CPU offload**：KTransformers 可将专家权重 offload 到内存/SSD，速度大幅下降，仅适合体验。

## GitHub Runner / Codespaces 限制（重要）

| 环境 | vCPU | 内存 | 磁盘 | GPU | 能否跑 BF16 |
|------|------|------|------|-----|-------------|
| GitHub 托管 Runner（最大） | 64 | 256 GB | 百 GB 级 | 无 | ❌ |
| Codespaces（最大） | 32 | 128 GB | 128 GB | 无（仅弱 GPU 档） | ❌ 差一个数量级 |
| 自托管 Runner（你的 GPU 机） | 任意 | 任意 | 任意 | 8×H200 等 | ✅ |

Codespaces 适合跑 7B–32B 小模型验证流水线，详见 [codespaces.md](codespaces.md)。
因此 `.github/workflows/deploy-glm-flash.yml` 固定使用 **自托管 Runner**
（标签 `self-hosted,linux,glm-flash`）。注册步骤见 README「方式一」。
自托管 Runner 机器即"本地"，工作流在其上执行下载、启动、测试、保活与回收。

## 网络与存储建议

- 首次下载 772GB：千兆内网约 2 小时，家庭宽带建议通宵；务必用支持断点续传的源
  （`hf download` / `modelscope` / aria2c manifest）。
- 权重放本地 NVMe；不要放网络盘（加载时随机读会拖垮启动）。
- 多卡节点确保 NVLink/PCIe 拓扑良好（`nvidia-smi topo -m`），TP 通信对带宽敏感。
