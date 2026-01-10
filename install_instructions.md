```bash

# Create a venv with UV and Python 3.12
uv venv .venv --python 3.12
source .venv/bin/activate

# Install Torch with GPU Support First!
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install PyscrAI
uv pip install -e .


# Verify GPU Support
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()} | GPU: {torch.cuda.get_device_name(0)}')"