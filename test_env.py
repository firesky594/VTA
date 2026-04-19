import cv2
import tensorrt as trt
import torch

print(f"PyTorch 版本: {torch.__version__}")
print(f"CUDA 是否可用: {torch.cuda.is_available()}")

if torch.cuda.is_available():
    print(f"显卡型号: {torch.cuda.get_device_name(0)}")
    print(f"CUDA 运行版本: {torch.version.cuda}")
    # 关键点：RTX 5080 应该返回 (10, 0)
    print(f"显卡算力 (Capability): {torch.cuda.get_device_capability(0)}")

    # 跑一个简单的矩阵乘法测试驱动程序
    x = torch.randn(1000, 1000).cuda()
    y = torch.randn(1000, 1000).cuda()
    z = torch.matmul(x, y)
    print("✅ PyTorch GPU 矩阵运算正常！")

# 1. 检查 TensorRT 库版本
print(f"TensorRT 版本: {trt.__version__}")

# 2. 检查 Torch 是否识别 GPU
print(f"PyTorch 是否可用 CUDA: {torch.cuda.is_available()}")

# 3. 核心测试：尝试创建一个 TensorRT 运行时
try:
    logger = trt.Logger(trt.Logger.INFO)
    runtime = trt.Runtime(logger)
    print("✅ TensorRT 运行时创建成功！系统已识别 TensorRT 环境。")
except Exception as e:
    print(f"❌ TensorRT 启动失败，请检查 DLL 路径。错误: {e}")

# 4. 检查 Torch-TensorRT 编译支持 (如果你安装了 torch-tensorrt)
try:
    import torch_tensorrt
    print("✅ Torch-TensorRT 已就绪，可以直接将 Torch 模型转换为 TRT。")
except ImportError:
    print("ℹ️ 未安装 torch-tensorrt，只能使用原生态 TensorRT API。")
print(cv2.__version__)
print(cv2.cuda.getCudaEnabledDeviceCount())  # 如果返回 0，说明这个 pip 包不支持 GP
