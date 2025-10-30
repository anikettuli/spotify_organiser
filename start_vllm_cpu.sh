#!/bin/bash
# This script starts the vLLM OpenAI-compatible server on the GPU.

echo "Starting vLLM server on GPU..."
echo "Model: unsloth/Qwen3-4B-Instruct-2507-unsloth-bnb-4bit (4-bit quantized)"
echo "This may take a while to download the model for the first time."
echo "Press Ctrl+C to stop the server."

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "Activated virtual environment"
fi

# Ensure vllm is installed
if ! python3 -c "import vllm" &> /dev/null; then
    echo "vllm not found. Please install it first by running: pip install vllm"
    exit 1
fi

# Use the simpler vllm serve command with memory limit
# --max-model-len 8192: Limit context to 8K tokens (fits in 8GB VRAM with quantized model)
# --gpu-memory-utilization 0.8: Use 80% of GPU memory
vllm serve "unsloth/Qwen3-4B-Instruct-2507-unsloth-bnb-4bit" \
    --gpu-memory-utilization 0.8 \
    --max-model-len 8192
