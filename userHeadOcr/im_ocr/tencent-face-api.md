# 腾讯云人脸识别 API - 人脸检测与属性分析

## 接口概述

**接口名称**：DetectFaceAttributes（人脸检测与属性分析）

**接口域名**：`iai.tencentcloudapi.com`

**接口版本**：`2020-03-03`

**接口描述**：检测给定图片中的人脸（Face）的位置、相应的面部属性和人脸质量信息，位置包括 (x，y，w，h)，面部属性包括性别（gender）、年龄（age）、表情（expression）、魅力（beauty）、眼镜（glass）、发型（hair）、口罩（mask）和姿态 (pitch，roll，yaw)。

## 应用场景

1. **人员库创建人员/增加人脸**：保证人员人脸信息的质量，便于后续的业务处理。
2. **人脸搜索**：保证输入的图片质量，快速准确匹配到对应的人员。
3. **人脸验证**：保证人脸信息的质量，避免明明是本人却认证不通过的情况。
4. **人脸融合**：保证上传的人脸质量，人脸融合的效果更好。

## 输入参数

| 参数名称                | 必选 | 类型      | 描述                                                                                                                                                                                                                                                                                                                                          |
| ------------------- | -- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Action              | 是  | String  | 公共参数，本接口取值：DetectFaceAttributes                                                                                                                                                                                                                                                                                 |
| Version             | 是  | String  | 公共参数，本接口取值：2020-03-03                                                                                                                                                                                                                                                                                           |
| Region              | 是  | String  | 公共参数，支持的地域：ap-beijing, ap-chengdu, ap-chongqing, ap-guangzhou, ap-nanjing, ap-shanghai, ap-singapore                                                                                                                                                                                         |
| MaxFaceNum          | 否  | Integer | 最多处理的人脸数目。默认值为1（仅检测图片中面积最大的那张人脸），最大值为120。此参数用于控制处理待检测图片中的人脸个数，值越小，处理速度越快。示例值：1                                                                                                                                                                                                                                                      |
| Image               | 否  | String  | 图片 base64 数据。base64 编码后大小不可超过5M。jpg格式长边像素不可超过4000，其他格式图片长边像素不可超2000。所有格式的图片短边像素不小于64。支持PNG、JPG、JPEG、BMP，不支持 GIF 图片。示例值：/9j/4AAQSkZJRg.....s97n//2Q==                                                                                                                                                                           |
| Url                 | 否  | String  | 图片的 Url。对应图片 base64 编码后大小不可超过5M。jpg格式长边像素不可超过4000，其他格式图片长边像素不可超2000。所有格式的图片短边像素不小于64。Url、Image必须提供一个，如果都提供，只使用 Url。图片存储于腾讯云的Url可保障更高下载速度和稳定性，建议图片存储于腾讯云。非腾讯云存储的Url速度和稳定性可能受一定影响。支持PNG、JPG、JPEG、BMP，不支持 GIF 图片。示例值：http://test.image.myqcloud.com/testA.jpg                                                          |
| FaceAttributesType  | 否  | String  | 是否返回年龄、性别、情绪等属性。合法值为（大小写不敏感）：None、Age、Beauty、Emotion、Eye、Eyebrow、Gender、Hair、Hat、Headpose、Mask、Mouth、Moustache、Nose、Shape、Skin、Smile。None为不需要返回。默认为 None。即FaceAttributesType属性为空时，各属性返回值为0。需要将属性组成一个用逗号分隔的字符串，属性之间的顺序没有要求。关于各属性的详细描述，参见下文出参。最多返回面积最大的 5 张人脸属性信息，超过 5 张人脸（第 6 张及以后的人脸）的 AttributesInfo 不具备参考意义。示例值：Age,Gender,Beauty |
| NeedRotateDetection | 否  | Integer | 是否开启图片旋转识别支持。0为不开启，1为开启。默认为0。本参数的作用为，当图片中的人脸被旋转且图片没有exif信息时，如果不开启图片旋转识别支持则无法正确检测、识别图片中的人脸。若您确认图片包含exif信息或者您确认输入图中人脸不会出现被旋转情况，请不要开启本参数。开启后，整体耗时将可能增加数百毫秒。示例值：0                                                                                                                                                                   |
| FaceModelVersion    | 否  | String  | 人脸识别服务所用的算法模型版本。本接口仅支持"3.0"输入。示例值：3.0                                                                                                                                                                                                                                                                                                        |

## 输出参数

| 参数名称             | 类型                                                                | 描述                                                                                     |
| ---------------- | ----------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| ImageWidth       | Integer                                                           | 请求的图片宽度。示例值：550                                                                        |
| ImageHeight      | Integer                                                           | 请求的图片高度。示例值：366                                                                        |
| FaceDetailInfos  | Array of FaceDetailInfo                                          | 人脸信息列表。                                                                                |
| FaceModelVersion | String                                                            | 人脸识别所用的算法模型版本。示例值：3.0                                                                  |
| RequestId        | String                                                            | 唯一请求 ID，由服务端生成，每次请求都会返回（若请求因其他原因未能抵达服务端，则该次请求不会获得 RequestId）。定位问题时需要提供该次请求的 RequestId。 |

### FaceDetailInfo 结构

| 名称                       | 类型                                                    | 描述                                                                                                                                                                                                                                                                                           |
| ------------------------ | ----------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FaceRect                 | FaceRect                                               | 检测出的人脸框位置。                                                                                                                                                                                                                                                                                   |
| FaceDetailAttributesInfo | FaceDetailAttributesInfo                               | 人脸属性信息。根据 FaceAttributesType 输入的类型，返回年龄（Age）、颜值（Beauty）、情绪（Emotion）、眼睛信息（Eye）、眉毛（Eyebrow）、性别（Gender）、头发（Hair）、帽子（Hat）、姿态（Headpose）、口罩（Mask）、嘴巴（Mouth）、胡子（Moustache） 、鼻子（Nose）、脸型（Shape）、肤色（Skin）、微笑（Smile）等人脸属性信息。若 FaceAttributesType 没有输入相关类型，则FaceDetaiAttributesInfo返回的细项不具备参考意义。 |

### FaceRect 结构

| 名称     | 类型      | 描述                                                                                                              |
| ------ | ------- | --------------------------------------------------------------------------------------------------------------- |
| X      | Integer | 人脸框左上角横坐标。人脸框包含人脸五官位置并在此基础上进行一定的扩展，若人脸框超出图片范围，会导致坐标负值。若需截取完整人脸，可以在完整分completess满足需求的情况下，将负值坐标取0。示例值：253 |
| Y      | Integer | 人脸框左上角纵坐标。人脸框包含人脸五官位置并在此基础上进行一定的扩展，若人脸框超出图片范围，会导致坐标负值。若需截取完整人脸，可以在完整分completess满足需求的情况下，将负值坐标取0。示例值：414 |
| Width  | Integer | 人脸宽度。示例值：180                                                                                                    |
| Height | Integer | 人脸高度。示例值：90                                                                                                     |

### FaceDetailAttributesInfo 主要属性说明

- **Age**：年龄，取值范围：[0,65]，其中65代表"65岁及以上"
- **Beauty**：美丑打分，取值范围：[0,100]
- **Emotion**：情绪，可识别自然、高兴、惊讶、生气、悲伤、厌恶、害怕
- **Eye**：眼睛相关信息，可识别是否戴眼镜、是否闭眼、是否双眼皮和眼睛大小
- **Eyebrow**：眉毛相关信息，可识别眉毛浓密、弯曲、长短信息
- **Gender**：性别信息，0：男性，1：女性
- **Hair**：头发信息，包含头发长度、有无刘海、头发颜色
- **Hat**：帽子信息，可识别是否佩戴帽子、帽子款式、帽子颜色
- **HeadPose**：姿态信息，包含人脸的上下偏移（Pitch）、左右偏移（Yaw）、平面旋转（Roll）信息
- **Mask**：口罩佩戴信息，0: 无口罩，1: 有口罩不遮脸，2: 有口罩遮下巴，3: 有口罩遮嘴，4: 正确佩戴口罩
- **Mouth**：嘴巴信息，可识别是否张嘴、嘴唇厚度
- **Moustache**：胡子信息，0：无胡子，1：有胡子
- **Nose**：鼻子信息，0：朝天鼻，1：鹰钩鼻，2：普通，3：圆鼻头
- **Shape**：脸型信息，0：方脸，1：三角脸，2：鹅蛋脸，3：心形脸，4：圆脸
- **Skin**：肤色信息，0：黄色皮肤，1：棕色皮肤，2：黑色皮肤，3：白色皮肤
- **Smile**：微笑程度，取值范围：[0,100]

## 错误码

| 错误码                                           | 描述                          |
| --------------------------------------------- | --------------------------- |
| AuthFailure.InvalidAuthorization              | 认证失败。                       |
| FailedOperation.FaceSizeTooSmall              | 人脸框大小小于MinFaceSize设置，人脸被过滤。 |
| FailedOperation.ImageDecodeFailed             | 图片解码失败。                     |
| FailedOperation.ImageDownloadError            | 图片下载错误。                     |
| FailedOperation.ImageResolutionExceed         | 图片分辨率过大。                    |
| FailedOperation.ImageResolutionTooSmall       | 图片短边分辨率小于64。                |
| FailedOperation.ImageSizeExceed               | base64编码后的图片数据大小不超过5M。      |
| FailedOperation.RequestLimitExceeded          | 请求频率超过限制。                   |
| FailedOperation.RequestTimeout                | 后端服务超时。                     |
| FailedOperation.RpcFail                       | Rpc调用失败。                    |
| FailedOperation.ServerError                   | 算法服务异常，请重试。                 |
| FailedOperation.UnKnowError                   | 内部错误。                       |
| InternalError                                 | 内部错误。                       |
| InvalidParameter.InvalidParameter             | 参数不合法。                      |
| InvalidParameterValue.FaceModelVersionIllegal | 算法模型版本不合法。                  |
| InvalidParameterValue.ImageEmpty              | 图片为空。                       |
| InvalidParameterValue.NoFaceInPhoto           | 图片中没有人脸。                    |
| InvalidParameterValue.UrlIllegal              | URL格式不合法。                   |
| LimitExceeded.ErrorFaceNumExceed              | 人脸个数超过限制。                   |
| MissingParameter.ErrorParameterEmpty          | 必选参数为空。                     |
| ResourceUnavailable.Delivering                | 资源正在发货中。                    |
| ResourceUnavailable.Freeze                    | 账号已被冻结。                     |
| ResourceUnavailable.InArrears                 | 账号已欠费。                      |
| ResourceUnavailable.LowBalance                | 余额不足。                       |
| ResourceUnavailable.NotExist                  | 计费状态未知，请确认是否已在控制台开通服务。      |
| ResourceUnavailable.Recover                   | 资源已被回收。                     |
| ResourceUnavailable.StopUsing                 | 账号已停服。                      |
| ResourceUnavailable.UnknownStatus             | 计费状态未知。                     |
| ResourcesSoldOut.ChargeStatusException        | 计费状态异常。                     |
| UnsupportedOperation.UnknowMethod             | 未知方法名。                      |

## 示例

### 成功示例

**输入示例**：
```json
{
    "Url": "http://test.image.myqcloud.com/testA.jpg",
    "FaceAttributesType": "Age,Gender,Beauty",
    "MaxFaceNum": 1
}
```

**输出示例**：
```json
{
    "Response": {
        "ImageWidth": 550,
        "ImageHeight": 366,
        "FaceModelVersion": "3.0",
        "FaceDetailInfos": [
            {
                "FaceRect": {
                    "X": 375,
                    "Y": 37,
                    "Width": 63,
                    "Height": 82
                },
                "FaceDetailAttributesInfo": {
                    "Age": 30,
                    "Beauty": 75,
                    "Gender": {
                        "Type": 0,
                        "Probability": 0.95
                    }
                }
            }
        ],
        "RequestId": "b2c154b9-4620-4d37-8fd1-f6af3748f998"
    }
}
```

### 失败示例

**输出示例**：
```json
{
    "Response": {
        "RequestId": "ab0ebc1d-7a0e-4327-808b-3d24322a97dd",
        "Error": {
            "Code": "InvalidParameterValue.NoFaceInPhoto",
            "Message": "图片中没有人脸。"
        }
    }
}
```

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

4. **签名方式**：
   - 公共参数中的签名方式请使用V3版本，即配置SignatureMethod参数为TC3-HMAC-SHA256

## 参考文档

- [腾讯云人脸识别 API 文档](https://cloud.tencent.com/document/product/867/47396)
- [数据结构说明](https://cloud.tencent.com/document/api/867/45020#FaceDetailInfo)
- [腾讯云 API 平台](https://console.cloud.tencent.com/api/explorer?Product=iai&Version=2020-03-03&Action=DetectFaceAttributes)
