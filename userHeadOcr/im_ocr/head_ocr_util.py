#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
头像 OCR 检测工具 - 兼容本地图片和URL版本
功能：检测图片中是否存在正确的头像
支持三种类型的输入：
1. 本地图片文件（相对路径或绝对路径）- 转为base64后使用Image参数
2. 直接图片URL - 使用Url参数
3. 百度图片搜索URL - 自动提取实际图片URL后使用Url参数
"""

from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.iai.v20200303 import iai_client, models
import json
import os
import base64
import urllib.parse
import io
from pathlib import Path
from typing import Union, Dict, Any
from enum import Enum

# 尝试加载 .env 文件
try:
    from dotenv import load_dotenv, find_dotenv
    # 自动查找并加载 .env 文件
    # find_dotenv() 会从当前目录向上递归查找 .env 文件
    load_dotenv(find_dotenv())
except ImportError:
    # 如果没有安装 python-dotenv，跳过加载 .env 文件
    pass


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
    
    # 遮挡检查阈值 (0-100，数值越小表示遮挡越严重，数值越大表示越完整)
    # 建议阈值：50-60
    COMPLETENESS_THRESHOLD = 50

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
        如果图片过大，会自动压缩
        
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
        # Base64编码后大小约为原始大小的4/3，所以原始大小超过3.75MB就有可能超标
        # 这里为了保险起见，设定阈值为3.5MB
        file_size = os.path.getsize(file_path)
        if file_size > 3.5 * 1024 * 1024:  # 3.5MB
            return self._compress_image(file_path)
        
        # 读取文件并转换为base64
        try:
            with open(file_path, 'rb') as f:
                image_data = f.read()
                base64_data = base64.b64encode(image_data).decode('utf-8')
                
                # 再次检查base64编码后的大小
                base64_size = len(base64_data)
                if base64_size > 5 * 1024 * 1024:  # 5MB
                    # 如果还是太大，尝试压缩
                    return self._compress_image(file_path)
                
                return base64_data
        except Exception as e:
            raise IOError(f"读取图片文件失败: {str(e)}")

    def _compress_image(self, file_path: str) -> str:
        """
        压缩图片到指定大小以下并转换为base64
        目标是base64编码后小于5MB (即二进制小于3.75MB)
        """
        try:
            from PIL import Image as PILImage
        except ImportError:
            raise IOError("图片过大且未安装Pillow库，无法进行压缩处理")

        # 目标大小：3.5MB (留有余量)
        target_size = 3.5 * 1024 * 1024
        
        try:
            with PILImage.open(file_path) as img:
                # 转换为RGB (去除Alpha通道，因为JPEG不支持)
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                # 初始参数
                quality = 85
                resize_ratio = 0.8
                width, height = img.size
                
                output_buffer = io.BytesIO()
                # 尝试保存
                img.save(output_buffer, format='JPEG', quality=quality)
                
                # 循环压缩直到满足大小要求
                while output_buffer.tell() > target_size and (quality > 10 or width > 200):
                    output_buffer = io.BytesIO()
                    
                    if quality > 30:
                        # 优先降低质量
                        quality -= 10
                    else:
                        # 质量已经很低了，开始缩小尺寸
                        width = int(width * resize_ratio)
                        height = int(height * resize_ratio)
                        if width < 100 or height < 100:
                            break
                        img = img.resize((width, height))
                    
                    img.save(output_buffer, format='JPEG', quality=quality)
                
                return base64.b64encode(output_buffer.getvalue()).decode('utf-8')
        except Exception as e:
            raise IOError(f"图片压缩失败: {str(e)}")
    
    def check_avatar(self, image_input: str, image_source: ImageSource = None) -> Dict[str, Any]:
        """
        检测图片中是否存在正确的头像
        支持三种类型的输入：
        1. 本地图片文件（相对路径或绝对路径）- 转为base64后使用Image参数
        2. 直接图片URL - 使用Url参数
        3. 百度图片搜索URL - 自动提取实际图片URL后使用Url参数
        
        Args:
            image_input: 图片输入（本地文件路径、URL或百度图片搜索URL）
            image_source: 图片来源枚举（可选，如果不提供则自动判断）
        
        Returns:
            dict: 检测结果
        """
        try:
            # 判断图片类型
            if image_source is None:
                image_source = self._get_image_type(image_input)
            
            # 调用 API 检测人脸
            req = models.DetectFaceAttributesRequest()
            req.MaxFaceNum = 5  # 检测多张人脸以进行数量校验
            req.FaceModelVersion = "3.0"
            # 只保留头像校验相关的属性
            # 增加 Mouth, Nose 以便潜在的属性检查，虽然遮挡主要靠 FaceQualityInfo
            req.FaceAttributesType = "Headpose,Mask,Glass,Eye,Mouth,Nose"
            # 开启质量检测以获取 Completeness (遮挡信息)
            # 注意：DetectFaceAttributes 接口可能不支持 NeedQualityDetection 参数，但默认可能返回相关信息
            # 如果不支持该参数，需要移除该行，依赖默认返回或改用 DetectFace 接口
            # req.NeedQualityDetection = 1
            
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
            
            # 检查人脸数量（必须严格为1）
            if len(resp.FaceDetailInfos) > 1:
                return {
                    "hasValidAvatar": False,
                    "faceCount": len(resp.FaceDetailInfos),
                    "message": f"图片中检测到 {len(resp.FaceDetailInfos)} 张人脸，只允许包含一张人脸",
                    "imagePath": actual_image_path,
                    "imageSource": image_source.value
                }
            
            # 获取第一张人脸（最大的人脸）
            face_info = resp.FaceDetailInfos[0]
            face_rect = face_info.FaceRect
            attrs = face_info.FaceDetailAttributesInfo
            quality = getattr(face_info, "FaceQualityInfo", None)
            
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
            
            # 收集所有校验错误
            validation_errors = []
            
            # 1. 检查姿态
            head_pose = attrs.HeadPose if attrs else None
            if head_pose:
                pose_check = self._check_head_pose(head_pose)
                if not pose_check["valid"]:
                    validation_errors.append(pose_check["message"])
            
            # 2. 检查口罩
            mask = attrs.Mask if attrs else None
            if mask:
                mask_check = self._check_mask(mask)
                if not mask_check["valid"]:
                    validation_errors.append(mask_check["message"])
            
            # 3. 检查眼镜
            # 注意: Glass 通常包含在 Eye 中，或者 SDK 结构中 Glass 在 Eye 下
            glass = attrs.Eye.Glass if attrs and attrs.Eye else None
            if glass:
                glass_check = self._check_glass(glass)
                if not glass_check["valid"]:
                    validation_errors.append(glass_check["message"])
            
            # 4. 检查眼睛
            eye = attrs.Eye if attrs else None
            if eye:
                eye_check = self._check_eye(eye)
                if not eye_check["valid"]:
                    validation_errors.append(eye_check["message"])

            # 5. 检查遮挡 (FaceQualityInfo.Completeness)
            if quality:
                occlusion_check = self._check_occlusion(quality)
                if not occlusion_check["valid"]:
                    validation_errors.append(occlusion_check["message"])

            # 提取校验相关的属性供返回
            attributes = {
                "glass": attrs.Eye.Glass.Type if attrs and attrs.Eye and attrs.Eye.Glass else None,
                "mask": attrs.Mask.Type if attrs and attrs.Mask else None,
                "eye_open": attrs.Eye.EyeOpen.Type if attrs and attrs.Eye and attrs.Eye.EyeOpen else None,
                "headpose": {
                    "pitch": head_pose.Pitch if head_pose else None,
                    "yaw": head_pose.Yaw if head_pose else None,
                    "roll": head_pose.Roll if head_pose else None
                } if head_pose else None,
                "completeness": {
                    "eye": quality.Completeness.Eye if quality and quality.Completeness else None,
                    "mouth": quality.Completeness.Mouth if quality and quality.Completeness else None,
                    "nose": quality.Completeness.Nose if quality and quality.Completeness else None
                } if quality else None
            }

            # Debug: check attributes content
            # for k, v in attributes.items():
            #    print(f"{k}: {type(v)} - {v}")
            
            # 如果有校验错误
            if validation_errors:
                return {
                    "hasValidAvatar": False,
                    "faceCount": len(resp.FaceDetailInfos),
                    "message": " | ".join(validation_errors),
                    "attributes": attributes,
                    "imagePath": actual_image_path,
                    "imageSource": image_source.value
                }
            
            # 所有检查通过
            return {
                "hasValidAvatar": True,
                "faceCount": len(resp.FaceDetailInfos),
                "message": "检测到有效头像",
                "attributes": attributes,
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
    
    def _check_head_pose(self, head_pose) -> Dict[str, Any]:
        """
        检查人脸姿态是否正常
        
        Args:
            head_pose: 姿态对象
        
        Returns:
            dict: {"valid": bool, "message": str}
        """
        if not head_pose:
            return {"valid": True, "message": ""}
        
        pitch = head_pose.Pitch
        yaw = head_pose.Yaw
        roll = head_pose.Roll
        
        # 检查上下偏移
        if pitch < self.PITCH_MIN or pitch > self.PITCH_MAX:
            return {
                "valid": False,
                "message": f"人脸上下偏移过大: {pitch}度（正常范围: {self.PITCH_MIN}~{self.PITCH_MAX}度）"
            }
        
        # 检查左右偏移
        if yaw < self.YAW_MIN or yaw > self.YAW_MAX:
            return {
                "valid": False,
                "message": f"人脸左右偏移过大: {yaw}度（正常范围: {self.YAW_MIN}~{self.YAW_MAX}度）"
            }
        
        # 检查平面旋转
        if roll < self.ROLL_MIN or roll > self.ROLL_MAX:
            return {
                "valid": False,
                "message": f"人脸旋转角度过大: {roll}度（正常范围: {self.ROLL_MIN}~{self.ROLL_MAX}度）"
            }
        
        return {"valid": True, "message": ""}
    
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
        
        # 允许：0（无口罩）
        # 禁止：其他任何类型（包括正确佩戴口罩）
        if mask.Type == 0:
            return {"valid": True, "message": ""}
        
        mask_types = {
            1: "有口罩但不遮脸",
            2: "有口罩遮下巴",
            3: "有口罩遮嘴",
            4: "正确佩戴口罩"
        }
        
        return {
            "valid": False,
            "message": f"检测到佩戴口罩: {mask_types.get(mask.Type, '未知')}"
        }



    def _check_glass(self, glass) -> Dict[str, Any]:
        """
        检查眼镜佩戴情况
        
        Args:
            glass: 眼镜对象
            
        Returns:
            dict: {"valid": bool, "message": str}
        """
        if not glass:
            return {"valid": True, "message": ""}
            
        # Type: 0-无眼镜, 1-普通眼镜, 2-墨镜
        if glass.Type == 2:
            return {"valid": False, "message": "检测到佩戴墨镜"}
            
        return {"valid": True, "message": ""}

    def _check_eye(self, eye) -> Dict[str, Any]:
        """
        检查眼睛闭合情况
        
        Args:
            eye: 眼睛对象
            
        Returns:
            dict: {"valid": bool, "message": str}
        """
        if not eye or not eye.EyeOpen:
            return {"valid": True, "message": ""}
            
        # EyeOpen.Type: 0-睁开, 1-闭眼
        if eye.EyeOpen.Type == 1:
            # 可以增加概率判断，例如 probability > 80
            return {"valid": False, "message": "检测到闭眼"}
            
        return {"valid": True, "message": ""}

    def _check_occlusion(self, quality) -> Dict[str, Any]:
        """
        检查五官遮挡情况 (基于 FaceQualityInfo.Completeness)
        
        Args:
            quality: 质量信息对象
            
        Returns:
            dict: {"valid": bool, "message": str}
        """
        if not quality or not quality.Completeness:
            # 如果没有质量信息，暂时认为通过（或者是API未返回）
            return {"valid": True, "message": ""}
            
        completeness = quality.Completeness
        threshold = self.COMPLETENESS_THRESHOLD
        
        errors = []
        
        # 检查眼睛完整度
        if completeness.Eye < threshold:
            errors.append(f"眼睛被遮挡(完整度{completeness.Eye}<{threshold})")
            
        # 检查嘴巴完整度
        if completeness.Mouth < threshold:
            errors.append(f"嘴巴被遮挡(完整度{completeness.Mouth}<{threshold})")
            
        # 检查鼻子完整度
        if completeness.Nose < threshold:
            errors.append(f"鼻子被遮挡(完整度{completeness.Nose}<{threshold})")
            
        if errors:
            return {"valid": False, "message": " | ".join(errors)}
            
        return {"valid": True, "message": ""}


def main():
    """示例用法"""
    # 配置信息 - 从环境变量或 .env 文件读取，避免硬编码敏感信息
    SECRET_ID = os.getenv("TENCENT_SECRET_ID")
    SECRET_KEY = os.getenv("TENCENT_SECRET_KEY")
    
    if not SECRET_ID or not SECRET_KEY:
        print("错误: 请设置 TENCENT_SECRET_ID 和 TENCENT_SECRET_KEY")
        print("\n方式1: 使用环境变量")
        print("  export TENCENT_SECRET_ID='your_secret_id'")
        print("  export TENCENT_SECRET_KEY='your_secret_key'")
        print("\n方式2: 使用 .env 文件（推荐）")
        print("  在项目根目录创建 .env 文件，内容如下：")
        print("  TENCENT_SECRET_ID=your_secret_id")
        print("  TENCENT_SECRET_KEY=your_secret_key")
        return
    
    # 创建检测器
    detector = HeadOCR(SECRET_ID, SECRET_KEY)
    
    # 示例1：使用本地图片文件（相对路径）
    # image_input = "../imgs/avatar_0001_20251208_101251_987477.jpg"
    # result = detector.check_avatar(image_input)  # 自动判断为本地文件
    
    # 也可以使用绝对路径
    # image_input = "/absolute/path/to/image.jpg"
    # result = detector.check_avatar(image_input, ImageSource.LOCAL_FILE)  # 显式指定来源

    # 示例2：直接图片URL
    image_input = "https://randomuser.me/api/portraits/men/1.jpg"
    # result = detector.check_avatar(image_input)  # 自动判断为直接URL
    # result = detector.check_avatar(image_input, ImageSource.DIRECT_URL)  # 显式指定来源
    
    # 示例3：百度图片搜索URL（会自动提取实际图片URL）
    # image_input = "https://image.baidu.com/search/detail?adpicid=0&b_applid=9789573169742938504&bdtype=0&commodity=&copyright=&cs=1850186389%2C55921271&di=7565560840087142401&fr=click-pic&fromurl=http%253A%252F%252Fwww.duitang.com%252Fblog%252F%253Fid%253D1512294406&gsm=78&hd=&height=0&hot=&ic=&ie=utf-8&imgformat=&imgratio=&imgspn=0&is=0%2C0&isImgSet=&latest=&lid=&lm=&objurl=https%253A%252F%252Fc-ssl.dtstatic.com%252Fuploads%252Fblog%252F202402%252F07%252FV2SOZWG9Cmg0Vq2.thumb.1000_0.png&os=1037517498%2C2535813189&pd=image_content&pi=0&pn=91&rn=1&simid=1850186389%2C55921271&tn=baiduimagedetail&width=0&word=%E7%9C%9F%E4%BA%BA%E5%A4%B4%E5%83%8F&z="
    # result = detector.check_avatar(image_input)  # 自动判断为百度URL
    # result = detector.check_avatar(image_input, ImageSource.BAIDU_URL)  # 显式指定来源
    
    result = detector.check_avatar(image_input)
    
    # 输出结果
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # 判断结果
    if result["hasValidAvatar"]:
        print(f"\n✓ 检测到有效头像，共 {result['faceCount']} 张人脸")
        print(f"  图片路径: {result.get('imagePath', 'unknown')}")
        print(f"  图片来源: {result.get('imageSource', 'unknown')}")
    else:
        print(f"\n✗ 未检测到有效头像: {result['message']}")
        print(f"  图片路径: {result.get('imagePath', 'unknown')}")
        print(f"  图片来源: {result.get('imageSource', 'unknown')}")


if __name__ == "__main__":
    main()
