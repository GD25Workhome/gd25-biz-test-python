# .env 文件配置说明

## 概述

项目已支持通过 `.env` 文件管理敏感配置信息（如腾讯云 API 密钥），避免硬编码到代码中。

## 配置步骤

### 1. 安装依赖

首先确保已安装 `python-dotenv` 依赖：

```bash
pip install python-dotenv
```

或使用项目的 requirements.txt：

```bash
pip install -r requirements.txt
```

### 2. 创建 .env 文件

在项目根目录下创建 `.env` 文件：

```bash
# 复制示例文件
cp .env.example .env

# 或手动创建
touch .env
```

### 3. 配置变量

编辑 `.env` 文件，填入真实的配置信息：

```env
# 腾讯云 Secret ID（必填）
TENCENT_SECRET_ID=AKIDxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 腾讯云 Secret Key（必填）
TENCENT_SECRET_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 腾讯云地域（可选，默认: ap-shanghai）
TENCENT_REGION=ap-shanghai
```

## .env 文件语法规则

### 基本语法

1. **键值对格式**：`KEY=VALUE`
   ```env
   TENCENT_SECRET_ID=your_secret_id
   ```

2. **等号前后可以有空格**（但不推荐）：
   ```env
   TENCENT_SECRET_ID = your_secret_id  # 不推荐，但有效
   ```

3. **值可以包含空格**（需要用引号包裹）：
   ```env
   SOME_VALUE="value with spaces"
   ```

4. **值可以包含特殊字符**（需要用引号包裹）：
   ```env
   PASSWORD="p@ssw0rd#123"
   ```

### 注释

- 使用 `#` 开头表示注释
- 注释可以单独一行，也可以跟在值后面
- 整行注释：
  ```env
  # 这是注释
  TENCENT_SECRET_ID=your_secret_id
  ```
- 行尾注释：
  ```env
  TENCENT_SECRET_ID=your_secret_id  # 这是注释
  ```

### 引号使用

1. **单引号**：保留字面值，不展开变量
   ```env
   VALUE='$HOME'  # 值就是字面量 $HOME
   ```

2. **双引号**：可以展开变量（如果支持）
   ```env
   VALUE="$HOME"  # 值会被展开为实际路径
   ```

3. **无引号**：适用于简单值（无空格、无特殊字符）
   ```env
   TENCENT_SECRET_ID=AKIDxxxxxxxxx
   ```

### 多行值

使用三引号或反斜杠续行：

```env
# 方式1：使用反斜杠续行
MULTILINE_VALUE=line1 \
line2 \
line3

# 方式2：使用引号包裹多行（python-dotenv 支持）
MULTILINE_VALUE="line1
line2
line3"
```

### 变量引用

某些 .env 解析器支持变量引用：

```env
BASE_URL=https://api.example.com
API_URL=${BASE_URL}/v1
```

**注意**：`python-dotenv` 默认不支持变量展开，如需此功能需要使用其他库或自行处理。

### 空值

空值可以用以下方式表示：

```env
OPTIONAL_VALUE=
OPTIONAL_VALUE=""
```

## 环境变量优先级

代码会按以下优先级读取配置：

1. **系统环境变量**（最高优先级）
2. **.env 文件中的变量**（次优先级）
3. **默认值**（如果代码中设置了默认值）

这意味着：
- 如果同时设置了系统环境变量和 .env 文件，系统环境变量会优先
- 如果只设置了 .env 文件，会使用 .env 文件中的值
- 如果都没有设置，会使用代码中的默认值（如果有）

## 安全注意事项

1. **不要提交 .env 文件到 Git**
   - `.env` 文件已被 `.gitignore` 排除
   - 只提交 `.env.example` 作为模板

2. **不要分享 .env 文件**
   - 包含敏感信息，不要通过邮件、聊天工具等分享

3. **定期轮换密钥**
   - 如果密钥泄露，立即在腾讯云控制台重新生成

4. **不同环境使用不同配置**
   - 开发环境：`.env.development`
   - 测试环境：`.env.test`
   - 生产环境：使用系统环境变量或安全的配置管理系统

## 使用示例

### 示例1：基本配置

```env
# .env 文件
TENCENT_SECRET_ID=AKIDxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TENCENT_SECRET_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TENCENT_REGION=ap-shanghai
```

### 示例2：带注释的配置

```env
# 腾讯云 API 配置
# 获取方式：登录腾讯云控制台 -> 访问管理 -> API密钥管理

# Secret ID（必填）
TENCENT_SECRET_ID=AKIDxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Secret Key（必填）
TENCENT_SECRET_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 地域（可选，默认 ap-shanghai）
# 可选值: ap-beijing, ap-chengdu, ap-chongqing, ap-guangzhou, ap-nanjing, ap-shanghai, ap-singapore
TENCENT_REGION=ap-shanghai
```

### 示例3：多环境配置

```env
# .env.development（开发环境）
TENCENT_SECRET_ID=dev_secret_id
TENCENT_SECRET_KEY=dev_secret_key
TENCENT_REGION=ap-shanghai

# .env.production（生产环境）
TENCENT_SECRET_ID=prod_secret_id
TENCENT_SECRET_KEY=prod_secret_key
TENCENT_REGION=ap-shanghai
```

## 代码中的使用

代码会自动从 `.env` 文件加载配置，无需额外操作：

```python
import os
from dotenv import load_dotenv

# 加载 .env 文件（通常在模块导入时自动执行）
load_dotenv()

# 读取配置
secret_id = os.getenv("TENCENT_SECRET_ID")
secret_key = os.getenv("TENCENT_SECRET_KEY")
region = os.getenv("TENCENT_REGION", "ap-shanghai")  # 带默认值
```

## 常见问题

### Q1: .env 文件不生效？

**A**: 检查以下几点：
1. 确保 `.env` 文件在项目根目录
2. 确保已安装 `python-dotenv`
3. 确保代码中调用了 `load_dotenv()`
4. 检查变量名是否正确（区分大小写）

### Q2: 如何在不同环境使用不同配置？

**A**: 可以创建多个文件：
- `.env.development` - 开发环境
- `.env.test` - 测试环境
- `.env.production` - 生产环境

然后在代码中根据环境变量加载不同的文件：

```python
import os
from dotenv import load_dotenv

env = os.getenv("ENV", "development")
load_dotenv(f".env.{env}")
```

### Q3: 系统环境变量和 .env 文件哪个优先？

**A**: 系统环境变量优先级更高。如果同时设置了系统环境变量和 .env 文件，会使用系统环境变量的值。

### Q4: 值中包含等号怎么办？

**A**: 使用引号包裹：

```env
VALUE="key=value"
```

## 参考资源

- [python-dotenv 文档](https://github.com/theskumar/python-dotenv)
- [.env 文件规范](https://github.com/theskumar/python-dotenv#file-format)
