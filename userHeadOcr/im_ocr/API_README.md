# 腾讯云人脸识别 API 文档

本目录包含腾讯云人脸识别 API 的使用文档和示例代码。

## 文件说明

- `tencent-face-api.md` - API 接口详细文档，包含接口说明、参数说明、错误码等
- `python_example.py` - Python 调用示例代码
- `java_example.java` - Java 调用示例代码
- `README.md` - 本文件

## 快速开始

### Python 环境准备

1. 安装腾讯云 SDK：
```bash
pip install tencentcloud-sdk-python
```

2. 使用示例：
```python
from python_example import TencentFaceDetectClient

# 创建客户端
client = TencentFaceDetectClient(
    secret_id="your_secret_id",
    secret_key="your_secret_key",
    region="ap-shanghai"
)

# 检测人脸
result = client.detect_face_by_url(
    image_url="http://example.com/image.jpg",
    face_attributes_type="Age,Gender,Beauty",
    max_face_num=1
)
```

### Java 环境准备

1. 添加 Maven 依赖（在 `pom.xml` 中添加）：
```xml
<dependency>
    <groupId>com.tencentcloudapi</groupId>
    <artifactId>tencentcloud-sdk-java</artifactId>
    <version>3.1.xxx</version>
</dependency>

<!-- 如果使用人脸识别服务，需要添加以下依赖 -->
<dependency>
    <groupId>com.tencentcloudapi</groupId>
    <artifactId>tencentcloud-sdk-java-iai</artifactId>
    <version>3.1.xxx</version>
</dependency>

<!-- 项目已有 fastjson 依赖，无需重复添加 -->
<!-- 
<dependency>
    <groupId>com.alibaba</groupId>
    <artifactId>fastjson</artifactId>
    <version>1.2.83</version>
</dependency>
-->
```

**注意**：请将 `3.1.xxx` 替换为最新的版本号，可以在 [Maven Central](https://mvnrepository.com/artifact/com.tencentcloudapi/tencentcloud-sdk-java) 查看最新版本。

2. 使用示例：
```java
import com.yuehuijiankang.digital.example.TencentFaceDetectClient;

// 创建客户端
TencentFaceDetectClient client = new TencentFaceDetectClient(
    "your_secret_id",
    "your_secret_key",
    "ap-shanghai"
);

// 检测人脸
JSONObject result = client.detectFaceByUrl(
    "http://example.com/image.jpg",
    "Age,Gender,Beauty",
    1
);
```

## 配置信息

**注意**: 请使用环境变量或配置文件来管理敏感信息，不要硬编码到代码中。

**SecretId**: 请设置环境变量 `TENCENT_SECRET_ID` 或从配置文件读取

**SecretKey**: 请设置环境变量 `TENCENT_SECRET_KEY` 或从配置文件读取

**使用环境变量的方式**:
```bash
export TENCENT_SECRET_ID='your_secret_id'
export TENCENT_SECRET_KEY='your_secret_key'
```

**支持的地域**：
- ap-beijing（北京）
- ap-chengdu（成都）
- ap-chongqing（重庆）
- ap-guangzhou（广州）
- ap-nanjing（南京）
- ap-shanghai（上海）
- ap-singapore（新加坡）

## 主要功能

### 1. 通过 URL 检测人脸
支持通过图片 URL 地址进行人脸检测。

### 2. 通过 Base64 检测人脸
支持通过 Base64 编码的图片数据进行人脸检测。

### 3. 通过本地文件检测人脸
支持通过本地图片文件进行人脸检测。

## 返回属性说明

可检测的人脸属性包括：
- **Age**: 年龄
- **Beauty**: 美丑打分
- **Emotion**: 情绪（自然、高兴、惊讶、生气、悲伤、厌恶、害怕）
- **Eye**: 眼睛信息（是否戴眼镜、是否闭眼、是否双眼皮、眼睛大小）
- **Eyebrow**: 眉毛信息（浓密、弯曲、长短）
- **Gender**: 性别
- **Hair**: 头发信息（长度、有无刘海、颜色）
- **Hat**: 帽子信息（是否佩戴、款式、颜色）
- **Headpose**: 姿态信息（上下偏移、左右偏移、平面旋转）
- **Mask**: 口罩佩戴信息
- **Mouth**: 嘴巴信息（是否张嘴、嘴唇厚度）
- **Moustache**: 胡子信息
- **Nose**: 鼻子信息
- **Shape**: 脸型信息
- **Skin**: 肤色信息
- **Smile**: 微笑程度

## 注意事项

1. **图片要求**：
   - base64 编码后大小不可超过5M
   - jpg格式长边像素不可超过4000，其他格式图片长边像素不可超2000
   - 所有格式的图片短边像素不小于64
   - 支持PNG、JPG、JPEG、BMP，不支持 GIF 图片

2. **人脸数量限制**：
   - 最多返回面积最大的 5 张人脸属性信息
   - 超过 5 张人脸（第 6 张及以后的人脸）的 AttributesInfo 不具备参考意义

3. **属性返回**：
   - 如果 FaceAttributesType 没有输入相关类型，则返回的细项不具备参考意义
   - 建议根据实际需求选择需要的属性类型，避免无效计算

## 参考文档

- [腾讯云人脸识别 API 文档](https://cloud.tencent.com/document/product/867/47396)
- [数据结构说明](https://cloud.tencent.com/document/api/867/45020#FaceDetailInfo)
- [腾讯云 API 平台](https://console.cloud.tencent.com/api/explorer?Product=iai&Version=2020-03-03&Action=DetectFaceAttributes)
