"""
gpu_check.py — Apple Silicon MPS 가속 점검 (PDF #15 §1 Mac 패치판)

입력: 없음
출력: torch/MPS 정보 콘솔
실행: source .venv/bin/activate && python gpu_check.py
"""
import torch

print(f"PyTorch 버전: {torch.__version__}")
print(f"CUDA 사용 가능: {torch.cuda.is_available()}")
print(f"MPS 사용 가능: {torch.backends.mps.is_available()}")
print(f"MPS 빌드됨: {torch.backends.mps.is_built()}")

if torch.backends.mps.is_available():
    print("→ Apple Silicon MPS 가속으로 추론합니다.")
    device = torch.device("mps")
    x = torch.ones(3, device=device)
    print(f"  MPS 텐서 테스트: {x}")
elif torch.cuda.is_available():
    print(f"GPU 이름: {torch.cuda.get_device_name(0)}")
    print(f"GPU 메모리: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
else:
    print("→ MPS/CUDA 모두 없음. CPU로 실행됩니다.")
