# Yolov8-onnx-deepstream-python

简单的yolov8模型4分类车辆检测器，代码很简陋

##


##

### Requirements


#### DeepStream 6.0.1 / 6.0 on x86 platform

* [Ubuntu 18.04](https://releases.ubuntu.com/18.04.6/)
* [CUDA 11.4 Update 1](https://developer.nvidia.com/cuda-11-4-1-download-archive?target_os=Linux&target_arch=x86_64&Distribution=Ubuntu&target_version=18.04&target_type=runfile_local)
* [TensorRT 8.0 GA (8.0.1)](https://developer.nvidia.com/nvidia-tensorrt-8x-download)
* [NVIDIA Driver 470.63.01](https://www.nvidia.com.br/Download/index.aspx)
* [NVIDIA DeepStream SDK 6.0.1 / 6.0](https://developer.nvidia.com/deepstream-sdk-download-tesla-archived)
* [GStreamer 1.14.5](https://gstreamer.freedesktop.org/)
* requirement.txt 仅可作为参考，有许多是不需要的



##

### 基础

#### 1. 下载工程，进入路径

```
cd yolov8_onnx_deepstream_python
```

#### 2. yolov8导出的onnx模型移至`weights`，修改`onnx2tensorrt.py`对应路径
```
# onnx2tensorrt.py
onnx_path = './weights/best.onnx'
engine_path = './weights/best.engine'

python onnx2tensorrt.py # 简单转换不涉及动态形状、int8量化
```

#### 3. 编译yolov8解析函数
```
cd model
make
```

#### 4. 根据模型修改`config_infer_primary.txt` 
#### 5. 运行

```
python main.py
```


### NMS Configuration

To change the `nms-iou-threshold`, `pre-cluster-threshold` and `topk` values, modify the config_infer file and regenerate the model engine file

```
[class-attrs-all]
nms-iou-threshold=0.45
pre-cluster-threshold=0.25
topk=300
```

**NOTE**: It is important to regenerate the engine to get the max detection speed based on `pre-cluster-threshold` you set.

**NOTE**: Lower `topk` values will result in more performance.

**NOTE**: Make sure to set `cluster-mode=2` in the config_infer file.

## References
+ [wang-xinyu/tensorrtx](https://github.com/wang-xinyu/tensorrtx)
+ [NVIDIA-AI-IOT/deepstream_python_apps](https://github.com/NVIDIA-AI-IOT/deepstream_python_apps)
+ [Deepstream-Yolo](https://github.com/marcoslucianops/DeepStream-Yolo)