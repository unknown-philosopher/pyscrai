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

# Ubuntu required updates 
 sudo apt update && sudo apt install -y libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev libgstreamer-plugins-bad1.0-dev gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav gstreamer1.0-tools gstreamer1.0-x gstreamer1.0-alsa gstreamer1.0-gl gstreamer1.0-gtk3 gstreamer1.0-qt5 gstreamer1.0-pulseaudio