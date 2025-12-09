from fastapi import FastAPI, HTTPException, Body, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
from pathlib import Path
import sys
import requests
import datetime
import os
import base64
import json
import shutil
import urllib.parse
from enum import Enum
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.iai.v20200303 import iai_client, models

# Add current directory to path to import jsonline
sys.path.append(str(Path(__file__).parent))

# 尝试加载 .env 文件
try:
    from dotenv import load_dotenv, find_dotenv
    # 自动查找并加载 .env 文件
    # find_dotenv() 会从当前目录向上递归查找 .env 文件
    load_dotenv(find_dotenv())
except ImportError:
    # 如果没有安装 python-dotenv，跳过加载 .env 文件
    pass

from jsonline import JsonLineDB

class ImageSource(Enum):
    """图片来源枚举"""
    LOCAL_FILE = "local_file"      # 本地文件
    DIRECT_URL = "direct_url"     # 直接图片URL
    BAIDU_URL = "baidu_url"       # 百度图片搜索URL


class HeadOCR:
    """头像 OCR 检测器（本地图片专用）"""
    
    # 姿态检查阈值
    PITCH_MIN = -10  # 上下偏移最小值
    PITCH_MAX = 10   # 上下偏移最大值
    YAW_MIN = -10    # 左右偏移最小值
    YAW_MAX = 10     # 左右偏移最大值
    ROLL_MIN = -20   # 平面旋转最小值
    ROLL_MAX = 20    # 平面旋转最大值
    
    def __init__(self, secret_id: str, secret_key: str, region: str = 'ap-shanghai'):
        """
        初始化检测器
        
        Args:
            secret_id: 腾讯云 SecretId
            secret_key: 腾讯云 SecretKey
            region: 地域，默认 ap-shanghai
        """
        # 实例化认证对象
        cred = credential.Credential(secret_id, secret_key)
        
        # 实例化http选项
        http_profile = HttpProfile()
        http_profile.endpoint = "iai.tencentcloudapi.com"
        http_profile.reqTimeout = 30
        
        # 实例化client选项
        client_profile = ClientProfile()
        client_profile.httpProfile = http_profile
        client_profile.signMethod = "TC3-HMAC-SHA256"
        
        # 实例化客户端
        self.client = iai_client.IaiClient(cred, region, client_profile)
    
    def _is_relative_path(self, path: str) -> bool:
        """
        判断是否为相对路径
        
        Args:
            path: 路径字符串
        
        Returns:
            bool: 是否为相对路径
        """
        # 检查是否是URL（以http://或https://开头）
        if path.startswith(('http://', 'https://')):
            return False
        
        # 检查是否是绝对路径（Unix系统以/开头，Windows系统以盘符开头）
        if os.path.isabs(path):
            return False
        
        # 其他情况视为相对路径
        return True
    
    def _is_baidu_image_url(self, url: str) -> bool:
        """
        判断是否为百度图片搜索URL
        
        Args:
            url: URL字符串
        
        Returns:
            bool: 是否为百度图片搜索URL
        """
        return 'image.baidu.com' in url or ('baidu.com' in url and 'objurl' in url)
    
    def _get_image_type(self, image_input: str) -> ImageSource:
        """
        判断图片输入的类型
        
        Args:
            image_input: 图片输入（相对路径、绝对路径、URL或百度图片搜索URL）
        
        Returns:
            ImageSource: 图片来源枚举
        """
        if self._is_relative_path(image_input) or os.path.isabs(image_input):
            return ImageSource.LOCAL_FILE
        elif self._is_baidu_image_url(image_input):
            return ImageSource.BAIDU_URL
        else:
            return ImageSource.DIRECT_URL
    
    def _extract_image_url(self, url: str) -> str:
        """
        从URL中提取实际的图片URL
        支持百度图片、Google图片等需要提取实际图片URL的情况
        
        Args:
            url: 原始URL
        
        Returns:
            str: 实际的图片URL
        """
        # 如果是百度图片搜索URL，提取objurl参数
        if 'image.baidu.com' in url or 'baidu.com' in url:
            try:
                parsed = urllib.parse.urlparse(url)
                params = urllib.parse.parse_qs(parsed.query)
                if 'objurl' in params:
                    objurl = params['objurl'][0]
                    # URL解码
                    actual_url = urllib.parse.unquote(objurl)
                    return actual_url
            except Exception:
                pass
        
        # 如果是Google图片URL，提取imgurl参数
        if 'google.com' in url or 'googleusercontent.com' in url:
            try:
                parsed = urllib.parse.urlparse(url)
                params = urllib.parse.parse_qs(parsed.query)
                if 'imgurl' in params:
                    return params['imgurl'][0]
            except Exception:
                pass
        
        # 其他情况直接返回原URL
        return url
    
    def _read_local_image_as_base64(self, file_path: str) -> str:
        """
        读取本地图片文件并转换为base64编码
        
        Args:
            file_path: 本地文件路径（相对路径或绝对路径）
        
        Returns:
            str: base64编码的图片数据
        
        Raises:
            FileNotFoundError: 文件不存在
            IOError: 文件读取失败
        """
        # 如果是相对路径，需要转换为绝对路径
        if not os.path.isabs(file_path):
            # 获取当前脚本所在目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(current_dir, file_path)
        
        # 规范化路径（处理 ../ 等相对路径符号）
        file_path = os.path.normpath(file_path)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"图片文件不存在: {file_path}")
        
        # 检查文件大小（base64编码后不能超过5M）
        file_size = os.path.getsize(file_path)
        if file_size > 5 * 1024 * 1024:  # 5MB
            raise IOError(f"图片文件过大: {file_size} 字节，base64编码后可能超过5M限制")
        
        # 读取文件并转换为base64
        try:
            with open(file_path, 'rb') as f:
                image_data = f.read()
                base64_data = base64.b64encode(image_data).decode('utf-8')
                
                # 检查base64编码后的大小
                base64_size = len(base64_data)
                if base64_size > 5 * 1024 * 1024:  # 5MB
                    raise IOError(f"图片base64编码后大小超过5M限制: {base64_size} 字节")
                
                return base64_data
        except Exception as e:
            raise IOError(f"读取图片文件失败: {str(e)}")
    
    def check_avatar(self, image_input: str, image_source: ImageSource = None, 
                     pitch_min: float = None, pitch_max: float = None,
                     yaw_min: float = None, yaw_max: float = None,
                     roll_min: float = None, roll_max: float = None) -> Dict[str, Any]:
        """
        检测图片中是否存在正确的头像
        支持三种类型的输入：
        1. 本地图片文件（相对路径或绝对路径）- 转为base64后使用Image参数
        2. 直接图片URL - 使用Url参数
        3. 百度图片搜索URL - 自动提取实际图片URL后使用Url参数
        
        Args:
            image_input: 图片输入（本地文件路径、URL或百度图片搜索URL）
            image_source: 图片来源枚举（可选，如果不提供则自动判断）
            pitch_min: 上下偏移最小值（可选，覆盖默认值）
            pitch_max: 上下偏移最大值（可选，覆盖默认值）
            yaw_min: 左右偏移最小值（可选，覆盖默认值）
            yaw_max: 左右偏移最大值（可选，覆盖默认值）
            roll_min: 平面旋转最小值（可选，覆盖默认值）
            roll_max: 平面旋转最大值（可选，覆盖默认值）
        
        Returns:
            dict: 检测结果
        """
        # 使用传入的参数或默认参数
        current_pitch_min = pitch_min if pitch_min is not None else self.PITCH_MIN
        current_pitch_max = pitch_max if pitch_max is not None else self.PITCH_MAX
        current_yaw_min = yaw_min if yaw_min is not None else self.YAW_MIN
        current_yaw_max = yaw_max if yaw_max is not None else self.YAW_MAX
        current_roll_min = roll_min if roll_min is not None else self.ROLL_MIN
        current_roll_max = roll_max if roll_max is not None else self.ROLL_MAX

        try:
            # 判断图片类型
            if image_source is None:
                image_source = self._get_image_type(image_input)
            
            # 调用 API 检测人脸
            req = models.DetectFaceAttributesRequest()
            req.MaxFaceNum = 1  # 只检测最大的人脸
            req.FaceModelVersion = "3.0"
            # 需要返回姿态和口罩信息
            req.FaceAttributesType = "Headpose,Mask"
            
            # 根据图片类型设置不同的参数
            if image_source == ImageSource.LOCAL_FILE:
                # 类型1：本地文件，使用base64编码
                try:
                    base64_data = self._read_local_image_as_base64(image_input)
                    req.Image = base64_data
                    actual_image_path = os.path.normpath(
                        os.path.join(os.path.dirname(os.path.abspath(__file__)), image_input)
                        if not os.path.isabs(image_input) else image_input
                    )
                except FileNotFoundError as e:
                    return {
                        "hasValidAvatar": False,
                        "faceCount": 0,
                        "message": f"图片文件不存在: {str(e)}",
                        "imagePath": image_input,
                        "imageSource": image_source.value
                    }
                except IOError as e:
                    return {
                        "hasValidAvatar": False,
                        "faceCount": 0,
                        "message": f"读取图片文件失败: {str(e)}",
                        "imagePath": image_input,
                        "imageSource": image_source.value
                    }
            else:
                # 类型2或类型3：URL类型
                if image_source == ImageSource.BAIDU_URL:
                    # 类型3：百度图片搜索URL，提取实际图片URL
                    actual_image_url = self._extract_image_url(image_input)
                else:
                    # 类型2：直接图片URL
                    actual_image_url = image_input
                
                req.Url = actual_image_url
                actual_image_path = actual_image_url
            
            # 调用API
            resp = self.client.DetectFaceAttributes(req)
            
            # 检查是否检测到人脸
            if not resp.FaceDetailInfos or len(resp.FaceDetailInfos) == 0:
                return {
                    "hasValidAvatar": False,
                    "faceCount": 0,
                    "message": "图片中未检测到人脸",
                    "imagePath": actual_image_path,
                    "imageSource": image_source.value
                }
            
            # 获取第一张人脸（最大的人脸）
            face_info = resp.FaceDetailInfos[0]
            face_rect = face_info.FaceRect
            attrs = face_info.FaceDetailAttributesInfo
            
            # 检查人脸框
            if not self._check_face_rect(face_rect):
                return {
                    "hasValidAvatar": False,
                    "faceCount": len(resp.FaceDetailInfos),
                    "message": "人脸框不合理",
                    "details": {
                        "faceRect": {
                            "x": face_rect.X,
                            "y": face_rect.Y,
                            "width": face_rect.Width,
                            "height": face_rect.Height
                        }
                    },
                    "imagePath": actual_image_path,
                    "imageSource": image_source.value
                }
            
            # 检查姿态
            head_pose = attrs.HeadPose if attrs else None
            if head_pose:
                # 使用当前配置的阈值进行检查
                pose_check = self._check_head_pose_with_limits(
                    head_pose, 
                    current_pitch_min, current_pitch_max,
                    current_yaw_min, current_yaw_max,
                    current_roll_min, current_roll_max
                )
                if not pose_check["valid"]:
                    return {
                        "hasValidAvatar": False,
                        "faceCount": len(resp.FaceDetailInfos),
                        "message": pose_check["message"],
                        "details": {
                            "headPose": {
                                "pitch": head_pose.Pitch,
                                "yaw": head_pose.Yaw,
                                "roll": head_pose.Roll
                            }
                        },
                        "imagePath": actual_image_path,
                        "imageSource": image_source.value,
                        "config": {
                            "pitch_min": current_pitch_min, "pitch_max": current_pitch_max,
                            "yaw_min": current_yaw_min, "yaw_max": current_yaw_max,
                            "roll_min": current_roll_min, "roll_max": current_roll_max
                        }
                    }
            
            # 检查口罩遮挡
            mask = attrs.Mask if attrs else None
            if mask:
                mask_check = self._check_mask(mask)
                if not mask_check["valid"]:
                    return {
                        "hasValidAvatar": False,
                        "faceCount": len(resp.FaceDetailInfos),
                        "message": mask_check["message"],
                        "details": {
                            "mask": {
                                "type": mask.Type,
                                "probability": mask.Probability
                            }
                        },
                        "imagePath": actual_image_path,
                        "imageSource": image_source.value,
                        "config": {
                            "pitch_min": current_pitch_min, "pitch_max": current_pitch_max,
                            "yaw_min": current_yaw_min, "yaw_max": current_yaw_max,
                            "roll_min": current_roll_min, "roll_max": current_roll_max
                        }
                    }
            
            # 所有检查通过
            return {
                "hasValidAvatar": True,
                "faceCount": len(resp.FaceDetailInfos),
                "message": "检测到有效头像",
                "details": {
                    "faceRect": {
                        "x": face_rect.X,
                        "y": face_rect.Y,
                        "width": face_rect.Width,
                        "height": face_rect.Height
                    },
                    "headPose": {
                        "pitch": head_pose.Pitch if head_pose else None,
                        "yaw": head_pose.Yaw if head_pose else None,
                        "roll": head_pose.Roll if head_pose else None
                    } if head_pose else None,
                    "mask": {
                        "type": mask.Type if mask else None,
                        "probability": mask.Probability if mask else None
                    } if mask else None
                },
                "imagePath": actual_image_path,
                "imageSource": image_source.value,
                "config": {
                    "pitch_min": current_pitch_min, "pitch_max": current_pitch_max,
                    "yaw_min": current_yaw_min, "yaw_max": current_yaw_max,
                    "roll_min": current_roll_min, "roll_max": current_roll_max
                }
            }
            
        except Exception as e:
            error_code = getattr(e, 'code', None)
            error_message = getattr(e, 'message', str(e))
            
            # 处理特定错误
            if error_code == "InvalidParameterValue.NoFaceInPhoto":
                return {
                    "hasValidAvatar": False,
                    "faceCount": 0,
                    "message": "图片中未检测到人脸",
                    "imagePath": image_input,
                    "imageSource": image_source.value if 'image_source' in locals() else "unknown"
                }
            
            return {
                "hasValidAvatar": False,
                "faceCount": 0,
                "message": f"检测失败: {error_message}",
                "error": {
                    "code": error_code,
                    "message": error_message
                },
                "imagePath": image_input,
                "imageSource": image_source.value if 'image_source' in locals() else "unknown"
            }
    
    def _check_face_rect(self, face_rect) -> bool:
        """
        检查人脸框是否合理
        
        Args:
            face_rect: 人脸框对象
        
        Returns:
            bool: 是否合理
        """
        if not face_rect:
            return False
        
        # 检查宽度和高度
        if face_rect.Width <= 0 or face_rect.Height <= 0:
            return False
        
        # 人脸框大小不能太小（至少 20x20 像素）
        if face_rect.Width < 20 or face_rect.Height < 20:
            return False
        
        return True
    
    def _check_head_pose_with_limits(self, head_pose, 
                                     pitch_min, pitch_max, 
                                     yaw_min, yaw_max, 
                                     roll_min, roll_max) -> Dict[str, Any]:
        """
        使用指定阈值检查人脸姿态
        """
        if not head_pose:
            return {"valid": True, "message": ""}
        
        pitch = head_pose.Pitch
        yaw = head_pose.Yaw
        roll = head_pose.Roll
        
        # 检查上下偏移
        if pitch < pitch_min or pitch > pitch_max:
            return {
                "valid": False,
                "message": f"人脸上下偏移过大: {pitch}度（正常范围: {pitch_min}~{pitch_max}度）"
            }
        
        # 检查左右偏移
        if yaw < yaw_min or yaw > yaw_max:
            return {
                "valid": False,
                "message": f"人脸左右偏移过大: {yaw}度（正常范围: {yaw_min}~{yaw_max}度）"
            }
        
        # 检查平面旋转
        if roll < roll_min or roll > roll_max:
            return {
                "valid": False,
                "message": f"人脸旋转角度过大: {roll}度（正常范围: {roll_min}~{roll_max}度）"
            }
        
        return {"valid": True, "message": ""}
    
    def _check_head_pose(self, head_pose) -> Dict[str, Any]:
        """
        检查人脸姿态是否正常（使用默认阈值，保留以兼容旧代码）
        """
        return self._check_head_pose_with_limits(
            head_pose, 
            self.PITCH_MIN, self.PITCH_MAX,
            self.YAW_MIN, self.YAW_MAX,
            self.ROLL_MIN, self.ROLL_MAX
        )
    
    def _check_mask(self, mask) -> Dict[str, Any]:
        """
        检查口罩遮挡情况
        
        Args:
            mask: 口罩对象
        
        Returns:
            dict: {"valid": bool, "message": str}
        """
        if not mask:
            return {"valid": True, "message": ""}
        
        # Type: 0-无口罩, 1-有口罩不遮脸, 2-有口罩遮下巴, 3-有口罩遮嘴, 4-正确佩戴口罩
        # 允许：0（无口罩）和 4（正确佩戴口罩）
        if mask.Type == 0 or mask.Type == 4:
            return {"valid": True, "message": ""}
        
        mask_types = {
            1: "有口罩但不遮脸",
            2: "有口罩遮下巴",
            3: "有口罩遮嘴"
        }
        
        return {
            "valid": False,
            "message": f"口罩佩戴不正确: {mask_types.get(mask.Type, '未知')}"
        }


app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB
# Explicitly point to app_data.json
db_path = Path(__file__).parent / "data" / "app_data.json"
db = JsonLineDB(str(db_path))

# Mount Images
# Image path is ./imgs relative to this file
img_path = Path(__file__).parent / "imgs"
# Ensure the directory exists to avoid errors, though FastAPI might handle it
if not img_path.exists():
    print(f"Warning: Image path {img_path} does not exist. Creating it.")
    img_path.mkdir(parents=True, exist_ok=True)

app.mount("/images", StaticFiles(directory=str(img_path)), name="images")

# Pydantic Model
class Item(BaseModel):
    id: Optional[int] = None
    URL: Optional[str] = ""
    本地文件名: Optional[str] = ""  # Using Chinese key names as per data source
    下载时间: Optional[str] = ""
    ocr_result: Optional[str] = ""
    should_pass: Optional[bool] = None
    ocr_passed: Optional[bool] = None


# 注意: 必须从环境变量或 .env 文件读取敏感信息，不要硬编码
# 使用方式1: 环境变量
#   export TENCENT_SECRET_ID='your_secret_id'
#   export TENCENT_SECRET_KEY='your_secret_key'
# 使用方式2: .env 文件（推荐）
#   在项目根目录创建 .env 文件，内容如下：
#   TENCENT_SECRET_ID=your_secret_id
#   TENCENT_SECRET_KEY=your_secret_key
SECRET_ID = os.environ.get("TENCENT_SECRET_ID")
SECRET_KEY = os.environ.get("TENCENT_SECRET_KEY")
REGION = os.environ.get("TENCENT_REGION", "ap-shanghai")

# 检查必需的环境变量
if not SECRET_ID or not SECRET_KEY:
    raise ValueError(
        "请设置 TENCENT_SECRET_ID 和 TENCENT_SECRET_KEY\n"
        "\n方式1: 使用环境变量\n"
        "  export TENCENT_SECRET_ID='your_secret_id'\n"
        "  export TENCENT_SECRET_KEY='your_secret_key'\n"
        "\n方式2: 使用 .env 文件（推荐）\n"
        "  在项目根目录创建 .env 文件，内容如下：\n"
        "  TENCENT_SECRET_ID=your_secret_id\n"
        "  TENCENT_SECRET_KEY=your_secret_key"
    )

def download_image(url: str, item_id: int) -> str:
    """Download image from URL and return filename"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Determine extension from content-type or url
        content_type = response.headers.get('content-type')
        ext = '.jpg'
        if content_type == 'image/png':
            ext = '.png'
        elif content_type == 'image/jpeg':
            ext = '.jpg'
        elif content_type == 'image/gif':
            ext = '.gif'
            
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"avatar_{item_id:04d}_{timestamp}{ext}"
        filepath = img_path / filename
        
        with open(filepath, 'wb') as f:
            f.write(response.content)
            
        return filename
    except Exception as e:
        print(f"Download error: {e}")
        return ""

@app.get("/api/items")
async def get_items():
    items = db.read_all()
    # Sort by id descending
    return sorted(items, key=lambda x: int(x.get("id", 0)), reverse=True)

@app.post("/api/items")
async def create_item(
    url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    should_pass: Optional[bool] = Form(None)
):
    # Generate ID
    all_items = db.read_all()
    max_id = 0
    if all_items:
        try:
            max_id = max(int(i.get("id", 0)) for i in all_items)
        except:
            pass
    new_id = max_id + 1
    
    data = {
        "id": new_id,
        "URL": "",
        "本地文件名": "",
        "下载时间": "",
        "ocr_result": "",
        "should_pass": should_pass,
        "ocr_passed": None
    }
    
    if file:
        # Handle file upload
        try:
            ext = os.path.splitext(file.filename)[1]
            if not ext:
                ext = ".jpg" # Default
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"avatar_{new_id:04d}_{timestamp}{ext}"
            filepath = img_path / filename
            
            with open(filepath, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
                
            data["本地文件名"] = filename
            data["下载时间"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            data["URL"] = "" # Empty as requested
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {str(e)}")
            
    elif url:
        # Handle URL download
        filename = download_image(url, new_id)
        if not filename:
            raise HTTPException(status_code=400, detail="Failed to download image from URL")
            
        data["本地文件名"] = filename
        data["下载时间"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data["URL"] = url
        
    else:
        raise HTTPException(status_code=400, detail="Either URL or file must be provided")
    
    if db.upsert(data):
        return data
    raise HTTPException(status_code=500, detail="Failed to create item")

@app.put("/api/items/{item_id}")
async def update_item(item_id: int, item: Item):
    # Retrieve existing item to preserve other fields
    existing = db.get_by_id(item_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Item not found")
    
    data = item.model_dump(exclude_unset=True)
    
    # Only update URL if provided, and re-download
    if data.get("URL") and data["URL"] != existing.get("URL"):
        filename = download_image(data["URL"], item_id)
        data["本地文件名"] = filename
        data["下载时间"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        # If URL hasn't changed, keep existing file info unless explicitly cleared (which we don't expect from frontend)
        # But wait, requirement says "Only URL can be modified".
        # So we should take URL from input, and if it's different or forced, download.
        # Ideally, we merge new data into existing.
        pass

    # Merge: update existing with new data
    updated_data = {**existing, **data}
    updated_data["id"] = item_id # Ensure ID matches
    
    if db.upsert(updated_data):
        return updated_data
    raise HTTPException(status_code=500, detail="Failed to update item")

@app.delete("/api/items/{item_id}")
async def delete_item(item_id: int):
    if db.delete(item_id):
        return {"success": True}
    raise HTTPException(status_code=500, detail="Failed to delete item")

class OcrRequest(BaseModel):
    pitch_min: Optional[int] = -10
    pitch_max: Optional[int] = 10
    yaw_min: Optional[int] = -10
    yaw_max: Optional[int] = 10
    # Allow roll to be configured too if desired, but user focused on pitch/yaw
    # Defaulting roll to existing defaults just in case
    roll_min: Optional[int] = -20
    roll_max: Optional[int] = 20

@app.post("/api/items/{item_id}/ocr")
async def ocr_item(item_id: int, config: OcrRequest = Body(default=None)):
    item = db.get_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    filename = item.get("本地文件名")
    if not filename:
        raise HTTPException(status_code=400, detail="No local image found for this item")
    
    filepath = img_path / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Image file not found")
        
    # Initialize OCR (You need to set env vars or hardcode keys temporarily for demo)
    # WARNING: Please provide actual keys via environment variables
    ocr = HeadOCR(SECRET_ID, SECRET_KEY)
    
    # Use check_avatar from the imported HeadOCR class
    # Pass configuration from request
    if config:
        result = ocr.check_avatar(
            str(filepath), 
            pitch_min=config.pitch_min, pitch_max=config.pitch_max,
            yaw_min=config.yaw_min, yaw_max=config.yaw_max,
            roll_min=config.roll_min, roll_max=config.roll_max
        )
    else:
        result = ocr.check_avatar(str(filepath))
    
    # Save result as string (JSON dump) or specific fields
    # Requirement: "display OCR return result"
    result_str = json.dumps(result, ensure_ascii=False)
    item["ocr_result"] = result_str
    
    # Update ocr_passed based on result
    item["ocr_passed"] = result.get("hasValidAvatar")
    
    if db.upsert(item):
        return {
            "success": True, 
            "ocr_result": result_str,
            "ocr_passed": item["ocr_passed"]
        }
    
    raise HTTPException(status_code=500, detail="Failed to save OCR result")

# Mount Static (Frontend) - Must be last to not shadow APIs
# We serve the 'static' directory at the root
static_path = Path(__file__).parent / "static"
if not static_path.exists():
    static_path.mkdir(parents=True, exist_ok=True)
app.mount("/", StaticFiles(directory=str(static_path), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # Reload is useful for development
    uvicorn.run("backend:app", host="0.0.0.0", port=8000, reload=True)
