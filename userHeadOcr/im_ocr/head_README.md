# 头像检测功能说明

## 功能概述

检测图片 URL 中是否存在**正确的头像**。

## 判断标准

一个"正确的头像"需要满足以下条件：

1. **检测到人脸**：图片中至少检测到 1 张人脸
2. **人脸框合理**：人脸框大小和位置在合理范围内
3. **姿态正常**：人脸姿态（上下偏移、左右偏移、平面旋转）在可接受范围内
4. **无严重遮挡**：口罩遮挡情况可接受（允许无口罩或正确佩戴口罩）

## 接口说明

使用腾讯云人脸识别 API 的 `DetectFaceAttributes` 接口。

**接口域名**：`iai.tencentcloudapi.com`  
**接口版本**：`2020-03-03`

## 配置信息

**注意**: 请使用环境变量或配置文件来管理敏感信息，不要硬编码到代码中。

**SecretId**: 请设置环境变量 `TENCENT_SECRET_ID` 或从配置文件读取  
**SecretKey**: 请设置环境变量 `TENCENT_SECRET_KEY` 或从配置文件读取  
**推荐地域**: `ap-shanghai`（上海）

**使用环境变量的方式**:
```bash
export TENCENT_SECRET_ID='your_secret_id'
export TENCENT_SECRET_KEY='your_secret_key'
```

## 返回结果

```json
{
    "hasValidAvatar": true,  // 是否有正确的头像
    "faceCount": 1,          // 检测到的人脸数量
    "message": "检测到有效头像",  // 说明信息
    "details": {              // 详细信息（可选）
        "faceRect": {...},
        "headPose": {...}
    }
}
```

## 使用示例

### Python

```python
from avatar_detector import AvatarDetector

detector = AvatarDetector(
    secret_id="your_secret_id",
    secret_key="your_secret_key"
)

# 方式1：直接使用图片URL
result = detector.check_avatar(image_url="http://example.com/image.jpg")

# 方式2：使用百度图片搜索URL（会自动提取实际图片URL）
result = detector.check_avatar(image_url="https://image.baidu.com/search/detail?objurl=...")

print(result)
```

**注意**：程序会自动识别并提取以下类型的URL中的实际图片地址：
- 百度图片搜索URL（自动提取 `objurl` 参数）
- Google图片URL（自动提取 `imgurl` 参数）
- 其他直接图片URL（直接使用）

### Java

```java
import com.yuehuijiankang.digital.example.AvatarDetector;

AvatarDetector detector = new AvatarDetector(
    "your_secret_id",
    "your_secret_key"
);

JSONObject result = detector.checkAvatar("http://example.com/image.jpg");
System.out.println(result);
```

## 判断规则

### 1. 人脸框检查
- 人脸框宽度和高度必须大于 0
- 人脸框不能完全超出图片范围（允许部分超出）

### 2. 姿态检查
- **Pitch（上下偏移）**：范围 [-10, 10] 度
- **Yaw（左右偏移）**：范围 [-10, 10] 度  
- **Roll（平面旋转）**：范围 [-20, 20] 度

### 3. 遮挡检查
- 允许：无口罩（Type=0）或正确佩戴口罩（Type=4）
- 不允许：有口罩但不正确佩戴（Type=1,2,3）

## 错误处理

- 如果图片中没有人脸，返回 `hasValidAvatar: false`
- 如果图片下载失败或格式不支持，返回错误信息
- 如果 API 调用失败，返回错误详情

## 注意事项

1. **图片要求**：
   - 支持 PNG、JPG、JPEG、BMP 格式
   - 不支持 GIF 图片
   - 图片大小不超过 5M
   - 图片短边像素不小于 64

2. **性能考虑**：
   - 建议使用腾讯云存储的图片 URL，下载速度更快
   - 接口调用有频率限制，注意控制调用频率

3. **准确性**：
   - 本功能主要检测人脸是否存在和基本质量
   - 如需更严格的质量检测，建议使用 `DetectFace` 接口获取详细质量分数
