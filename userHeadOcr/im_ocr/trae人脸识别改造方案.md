# 人脸识别代码重构方案

## 1. 重构背景与目标
根据 [腾讯云人脸检测与属性分析接口文档](https://cloud.tencent.com/document/product/867/47396)，对现有的 `head_ocr_util.py` 进行重构。
主要目标：
1. **限制人脸数量**：严格限制图片中只能包含一张人脸。如果检测到多张人脸，则判定为不合格。
2. **优化属性识别**：`FaceAttributesType` 仅请求核心校验参数（姿态、口罩、眼镜、眼睛），移除性别、年龄、帽子等非必要属性。
3. **增强结果校验**：基于返回的 `FaceDetailInfos`，增加对头像质量的校验逻辑（如是否戴墨镜、帽子、闭眼等）。

## 2. 改造方案详情

### 2.1 请求参数优化 (`DetectFaceAttributesRequest`)

目前代码中 `FaceAttributesType` 仅设置为 `"Headpose,Mask"`。为了更好地评估头像质量，建议扩展为以下组合：

| 属性字段 | 说明 | 引入原因 |
| :--- | :--- | :--- |
| **Headpose** | 姿态 | 检测人脸是否过分侧偏、抬头或低头（现有逻辑保持） |
| **Mask** | 口罩 | 检测是否佩戴口罩，要求**严格禁止佩戴口罩** |
| **Glass** | 眼镜 | 检测是否佩戴墨镜，墨镜遮挡眼部特征 |
| **Eye** | 眼睛 | 检测眼睛睁闭状态，闭眼照片不适合作为头像 |

**修改计划**：
将 `FaceAttributesType` 设置为：`"Headpose,Mask,Glass,Eye"`。

### 2.2 校验逻辑增强 (`FaceDetailInfo`)

基于扩展后的属性，更新校验规则如下：

1.  **人脸数量 (FaceNum)**:
    *   校验规则：`len(FaceDetailInfos) == 1`。
    *   策略：如果检测到多张人脸，判定为不合格。
2.  **口罩检测 (Mask)**:
    *   校验规则：`Mask.Type != 0` (0:无口罩)。
    *   策略：**禁止佩戴口罩**。任何类型的口罩（包括正确佩戴）均视为不合格。
3.  **眼镜检测 (Glass)**:
    *   校验规则：`Glass.Type == 2` (墨镜)。
    *   策略：如果佩戴墨镜，判定为不合格。普通眼镜 (`Type == 1`) 允许。
4.  **眼睛状态 (Eye)**:
    *   校验规则：`Eye.EyeOpen < 50` (假设阈值，需根据 `EyeOpen` 具体的返回结构调整，文档中 `EyeOpen` 对应 `AttributeItem`，通常检查 `Type` 或 `Probability`)。
    *   修正：根据文档，`EyeOpen` 的 `Type` 为 0:睁开, 1:闭眼。
    *   策略：如果 `Type == 1` 且置信度高，判定为闭眼，建议不合格。

### 2.3 代码结构重构

建议将代码重构为更模块化的结构，分离“属性提取”和“规则校验”逻辑。

#### 修改后的 `check_avatar` 流程：
1.46→1.  **构建请求**：设置 `MaxFaceNum=5`（用于检测多脸）和精简后的 `FaceAttributesType`。
2.  **调用接口**：获取 `FaceDetailInfos`。
3.  **基础校验**：检查是否有人脸、人脸框大小（`FaceRect`）。
4.  **属性提取**：解析所有请求的属性到字典中。
5.  **规则校验**：遍历校验规则列表（姿态、遮挡、表情等）。
6.  **结果返回**：返回包含验证结果 `hasValidAvatar`、详细属性 `attributes` 和 失败原因 `reasons` 的结构化数据。

## 3. 预期返回数据结构

```json
{
    "hasValidAvatar": true,  // 或 false
    "message": "检测通过",   // 或 "检测失败：佩戴了墨镜"
    "attributes": {
        "glass": 0,          // 0:无, 1:普通, 2:墨镜
        "mask": 0,           // 0:无, 1:有...
        "eye_open": 0,       // 0:睁开, 1:闭眼
        "headpose": { ... }
    },
    "face_rect": { ... }
}
```

## 4. 下一步行动
1. 修改 `head_ocr_util.py` 中的 `FaceAttributesType`。
2. 增加 `_check_hat`, `_check_glass`, `_check_eye` 等私有校验方法。
3. 更新 `check_avatar` 的返回结构。
