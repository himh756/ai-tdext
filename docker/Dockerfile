# GLM-5.3-Flash vLLM 推理镜像
# 依赖 NVIDIA GPU + nvidia-container-toolkit；vLLM >= 0.29.0（含 FlashInfer >= 0.6.17）
FROM vllm/vllm-openai:nightly

LABEL org.opencontainers.image.title="glm-5.3-flash-vllm"
LABEL org.opencontainers.image.description="GLM-5.3-Flash (320B-A18B MoE) OpenAI-compatible serving via vLLM"

WORKDIR /app
COPY scripts/ /app/scripts/
COPY configs/ /app/configs/
RUN chmod +x /app/scripts/*.sh

# 默认环境变量（运行时可用 -e 或 env_file 覆盖）
ENV MODEL_ROOT=/models \
    TENSOR_PARALLEL_SIZE=8 \
    PORT=8000 \
    MAX_MODEL_LEN=131072 \
    GPU_MEMORY_UTILIZATION=0.92 \
    SERVED_MODEL_NAME=glm-5.3-flash \
    HF_ENDPOINT=https://hf-mirror.com

EXPOSE 8000

# 用法：
#   docker run --gpus all --ipc=host -p 8000:8000 \
#     -v ~/glm-models:/models:ro \
#     -e MODEL_PATH=/models/zai-org__GLM-5.3-Flash-BF16 \
#     glm-5.3-flash:vllm
ENTRYPOINT ["/app/scripts/serve_vllm.sh"]
