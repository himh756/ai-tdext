# 在 GitHub Codespaces（代码空间）里运行

> **先说结论：Codespaces 跑不了 GLM-5.3-Flash 本体，但可以跑 7B–32B 小模型，
> 用来完整验证本仓库的工作流、脚本和测试套件。**

## 为什么 Codespaces 跑不了 GLM-5.3-Flash

Codespaces 最大机器规格（2026-10 实测）：**32 核 / 128 GB 内存 / 128 GB 磁盘、无大显存 GPU**。

| 模型方案 | 权重大小 | 所需磁盘 | Codespaces（128GB 盘） | 结论 |
|----------|----------|----------|------------------------|------|
| GLM-5.3-Flash **BF16** | 772 GB | 1 TB+ | 128 GB | ❌ 差 8 倍 |
| GLM-5.3-Flash **FP8** | 386 GB | 500 GB+ | 128 GB | ❌ 差 4 倍 |
| GLM-5.3-Flash **NVFP4** | 229 GB | 300 GB+ | 128 GB | ❌ 差 2.5 倍（还需 Blackwell GPU） |
| GLM-5.3-Flash IQ2 GGUF | ~85 GB | ~110 GB | 128 GB | ⚠️ 勉强装下，但 CPU 推理 320B MoE 约 1 tok/s 以下，且免费存储额度仅 15GB/月，不实用 |
| **Qwen2.5-7B/14B/32B** | 4–20 GB | 10–40 GB | 128 GB | ✅ 完全可行 |

即：不是"差一点"，而是**差一个数量级**。模型推理需要 GPU 显存/大内存 + 大磁盘，
Codespaces 的定位是云端开发环境（写代码、跑测试），不是模型推理平台。

## 在 Codespaces 里验证本仓库（推荐小模型）

1. 仓库页 → **Code → Codespaces → Create codespace on main**（已内置 `.devcontainer/devcontainer.json`，
   自动装好 huggingface_hub / modelscope / llama-cpp-python）。
2. 选 **32 核 / 128GB** 机器类型（免费额度 120 核时/月 + 15GB 存储，超出按 $0.18/核时 + $0.07/GB月 计费）。
3. 跑通整条流水线（以小模型为例）：

   ```bash
   # 下载小模型（约 1GB）
   SOURCE=modelscope MODEL_ID=qwen/Qwen2.5-0.5B-Instruct-GGUF bash scripts/download_model.sh

   # 用 llama.cpp 起 OpenAI 兼容服务（CPU）
   python3 -m llama_cpp.server \
     --model ~/glm-models/qwen__Qwen2.5-0.5B-Instruct-GGUF/qwen2.5-0.5b-instruct-q4_0.gguf \
     --n_ctx 8192 --port 8000

   # 冒烟测试 + 完整测试套件（输入/输出全记录）
   MODEL=qwen2.5-0.5b-instruct-q4_0 bash scripts/smoke_test.sh
   MODEL=qwen2.5-0.5b-instruct-q4_0 python3 scripts/run_test_suite.py --out test-report.md
   ```

   报告 `test-report.md` 里每条用例的输入与输出都在，可直接下载。

4. 想验证 GLM 专属参数（`reasoning_effort` / `clear_thinking` / 工具调用），
   请在 GPU 机器上用 `serve_vllm.sh` 启动真正的 GLM-5.3-Flash 后再跑测试套件。

## GLM-5.3-Flash 本体的正确打开方式

| 方式 | 说明 |
|------|------|
| **自托管 Runner + Actions 工作流**（推荐） | 在 GPU 服务器注册 Runner，仓库页 Run workflow，全自动下载/启动/测试，报告进 Artifacts |
| GPU 云服务器 | 阿里云/腾讯云等租 8×H200（BF16）或 4×H200（FP8），按小时计费，用完释放 |
| 智谱云端 API | 零硬件，`glm-5.3-flash` 模型按量付费（见 `local-llm` 文档第 6 节） |
