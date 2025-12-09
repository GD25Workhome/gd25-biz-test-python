> 文件生成时间：2025年12月08日 00:00:00

# 头像 OCR 识别系统

> 最后更新时间：2025年12月08日 00:00:00

## 项目简介

这是一个基于 FastAPI 的 Web 应用系统，主要用于头像 OCR 识别和参数调优。系统通过集成腾讯云人脸识别 API，实现对头像图片的自动检测和验证，支持自定义人脸姿态阈值配置，帮助用户找到最佳的 OCR 识别参数。

### 核心功能

- 📸 **图片管理**：支持本地文件上传和 URL 下载两种方式添加图片
- 🔍 **头像 OCR 识别**：基于腾讯云人脸识别 API，检测头像的有效性
- ⚙️ **参数配置**：可自定义人脸姿态阈值（Pitch、Yaw、Roll）
- 📦 **批量处理**：支持批量 OCR 识别，提高处理效率
- 📊 **结果导出**：支持将识别结果导出为 Excel 文件
- 💾 **数据管理**：完整的 CRUD 操作，支持数据的增删改查

### 应用场景

- 头像审核系统：自动检测用户上传的头像是否符合规范
- 参数调优：通过大量样本测试，找到最佳的识别参数配置
- 数据标注：标记样本是否应该通过，用于训练和验证

## 项目结构

```
demo/
├── backend.py              # FastAPI 后端服务入口
├── jsonline.py             # JSONL 数据操作工具类
├── data/
│   └── app_data.json       # 数据存储文件（JSONL 格式）
├── imgs/                   # 图片存储目录
├── static/
│   └── index.html          # 前端单页面应用（Vue 3 + Element Plus）
├── cursor_docs/
│   └── 技术文档.md         # 详细技术文档
└── README.md               # 本文档
```

## 技术栈

- **后端**：Python 3.8+, FastAPI, 腾讯云人脸识别 API
- **前端**：Vue 3, Element Plus, Axios, SheetJS
- **数据存储**：JSONL 格式文件

## 快速开始

### 1. 环境要求

- Python 3.8+
- 腾讯云账号（需要开通人脸识别服务）

### 2. 安装依赖

```bash
pip install fastapi uvicorn python-multipart tencentcloud-sdk-python requests
```

或使用项目根目录的 `requirements.txt`：

```bash
pip install -r ../requirements.txt
```

### 3. 配置腾讯云密钥

设置环境变量（推荐）：

```bash
export TENCENT_SECRET_ID="your_secret_id"
export TENCENT_SECRET_KEY="your_secret_key"
```

或在 `backend.py` 中直接修改（仅用于开发测试）。

### 4. 启动服务

```bash
# 方式1：直接运行
python backend.py

# 方式2：使用 uvicorn
uvicorn backend:app --host 0.0.0.0 --port 8000 --reload
```

服务启动后，访问 [http://localhost:8000](http://localhost:8000) 即可使用。

## 使用说明

### 基本操作

1. **添加图片**
   - 点击"新增数据"按钮
   - 选择上传方式：本地文件或图片 URL
   - 填写"是否应该通过"（用于标注）
   - 保存

2. **OCR 识别**
   - 在 OCR 参数配置区域设置阈值（Pitch、Yaw、Roll）
   - 点击数据项右侧的"OCR识别"按钮
   - 查看识别结果摘要和详细参数

3. **批量处理**
   - 勾选多个数据项
   - 点击"批量OCR识别"按钮
   - 等待处理完成

4. **导出结果**
   - 点击"下载OCR结果"按钮
   - 自动下载 Excel 文件，包含所有数据和识别结果

5. **编辑/删除**
   - 点击"编辑"按钮修改 URL（会自动重新下载图片）
   - 点击"删除"按钮移除记录

### OCR 参数说明

- **Pitch（俯仰角）**：人脸上下偏移角度，默认范围 -10° ~ 10°
- **Yaw（偏航角）**：人脸左右偏移角度，默认范围 -10° ~ 10°
- **Roll（旋转角）**：人脸平面旋转角度，默认范围 -20° ~ 20°

系统提供两种预设配置：
- **腾讯云默认**：标准阈值配置
- **宽松配置**：放宽阈值范围，适合测试

## API 接口

### 数据管理

- `GET /api/items` - 获取所有数据
- `POST /api/items` - 新增数据（支持文件上传或 URL）
- `PUT /api/items/{id}` - 更新数据
- `DELETE /api/items/{id}` - 删除数据

### OCR 识别

- `POST /api/items/{id}/ocr` - 对指定图片进行 OCR 识别

### 静态资源

- `GET /images/{filename}` - 获取图片文件
- `GET /` - 前端页面

详细 API 文档请参考 [技术文档](./cursor_docs/技术文档.md)。

## 注意事项

⚠️ **重要提示**

1. **数据共享**：列表数据是共享的，请不要同时执行操作，避免结果相互覆盖
2. **API 密钥**：生产环境请使用环境变量配置密钥，不要硬编码
3. **API 限制**：注意腾讯云 API 的调用频率限制和费用
4. **数据备份**：建议定期备份 `data/app_data.json` 文件

## 详细文档

更多技术细节、架构设计、扩展建议等，请参考：

- [技术文档](./cursor_docs/技术文档.md) - 完整的技术文档，包含架构设计、API 详解、部署指南等

## 更新日志

### v1.0.0 (2025-12-08)
- 初始版本发布
- 实现基本的 CRUD 功能
- 集成腾讯云人脸识别 API
- 支持 OCR 参数配置
- 支持批量处理和结果导出
