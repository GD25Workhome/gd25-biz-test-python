#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
头像检测工具 - Python 版本
功能：检测图片 URL 中是否存在正确的头像
支持三种类型的图片输入：
1. 类型1：相对路径下的图片（本地文件）
2. 类型2：直接图片URL
3. 类型3：百度图片搜索URL（会自动提取实际图片URL）
"""

from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.iai.v20200303 import iai_client, models
import json
import urllib.parse
import re
import os
import base64
from pathlib import Path
from typing import Union, Dict, Any

# 尝试加载 .env 文件
try:
    from dotenv import load_dotenv
    # 从当前文件所在目录向上查找 .env 文件
    env_path = Path(__file__).parent.parent.parent.parent / '.env'
    load_dotenv(dotenv_path=env_path, override=False)
except ImportError:
    # 如果没有安装 python-dotenv，跳过加载 .env 文件
    pass


class AvatarDetector:
    """头像检测器"""
    
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
    
    def _get_image_type(self, image_input: str) -> str:
        """
        判断图片输入的类型
        
        Args:
            image_input: 图片输入（相对路径、URL或百度图片搜索URL）
        
        Returns:
            str: 图片类型 ('relative_path', 'direct_url', 'baidu_url')
        """
        if self._is_relative_path(image_input):
            return 'relative_path'
        elif self._is_baidu_image_url(image_input):
            return 'baidu_url'
        else:
            return 'direct_url'
    
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
            # 或者使用工作目录
            # current_dir = os.getcwd()
            file_path = os.path.join(current_dir, file_path)
        
        # 规范化路径（处理 ../ 等相对路径符号）
        file_path = os.path.normpath(file_path)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise FileNotFoundError(file_path)
        
        # 读取文件并转换为base64
        try:
            with open(file_path, 'rb') as f:
                image_data = f.read()
                base64_data = base64.b64encode(image_data).decode('utf-8')
                return base64_data
        except Exception as e:
            raise IOError(f"读取图片文件失败: {str(e)}")
    
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
    
    def check_avatar(self, image_input: str) -> Dict[str, Any]:
        """
        检测图片中是否存在正确的头像
        支持三种类型的输入：
        1. 相对路径下的图片（本地文件）
        2. 直接图片URL
        3. 百度图片搜索URL（会自动提取实际图片URL）
        
        Args:
            image_input: 图片输入（相对路径、URL或百度图片搜索URL）
        
        Returns:
            dict: 检测结果
            {
                "hasValidAvatar": bool,  # 是否有正确的头像
                "faceCount": int,        # 检测到的人脸数量
                "message": str,          # 说明信息
                "details": dict,         # 详细信息（可选）
                "imageType": str         # 图片类型
            }
        """
        try:
            # 判断图片类型
            image_type = self._get_image_type(image_input)
            
            # 调用 API 检测人脸
            req = models.DetectFaceAttributesRequest()
            req.MaxFaceNum = 1  # 只检测最大的人脸
            req.FaceModelVersion = "3.0"
            # 需要返回姿态和口罩信息
            req.FaceAttributesType = "Headpose,Mask"
            
            # 根据图片类型设置不同的参数
            if image_type == 'relative_path':
                # 类型1：相对路径，使用base64编码
                try:
                    base64_data = self._read_local_image_as_base64(image_input)
                    req.Image = base64_data
                except FileNotFoundError as e:
                    return {
                        "hasValidAvatar": False,
                        "faceCount": 0,
                        "message": f"图片文件不存在: {str(e)}",
                        "imageType": image_type
                    }
                except IOError as e:
                    return {
                        "hasValidAvatar": False,
                        "faceCount": 0,
                        "message": f"读取图片文件失败: {str(e)}",
                        "imageType": image_type
                    }
            else:
                # 类型2或类型3：URL类型
                if image_type == 'baidu_url':
                    # 类型3：百度图片搜索URL，提取实际图片URL
                    actual_image_url = self._extract_image_url(image_input)
                else:
                    # 类型2：直接图片URL
                    actual_image_url = image_input
                
                req.Url = actual_image_url
            
            # 调用API
            resp = self.client.DetectFaceAttributes(req)
            
            # 检查是否检测到人脸
            if not resp.FaceDetailInfos or len(resp.FaceDetailInfos) == 0:
                return {
                    "hasValidAvatar": False,
                    "faceCount": 0,
                    "message": "图片中未检测到人脸",
                    "imageType": image_type
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
                    "imageType": image_type
                }
            
            # 检查姿态
            head_pose = attrs.HeadPose if attrs else None
            if head_pose:
                pose_check = self._check_head_pose(head_pose)
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
                        "imageType": image_type
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
                        "imageType": image_type
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
                "imageType": image_type
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
                    "imageType": self._get_image_type(image_input) if 'image_input' in locals() else "unknown"
                }
            
            return {
                "hasValidAvatar": False,
                "faceCount": 0,
                "message": f"检测失败: {error_message}",
                "error": {
                    "code": error_code,
                    "message": error_message
                },
                "imageType": self._get_image_type(image_input) if 'image_input' in locals() else "unknown"
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
    detector = AvatarDetector(SECRET_ID, SECRET_KEY)
    
    # 示例1：类型1 - 相对路径下的图片（本地文件）
    # image_input = "avatar.jpg"  # 相对于脚本所在目录的路径
    # image_input = "../imgs/avatar_0001_20251208_101251_987477.jpg"  # 也可以使用相对路径
    
    # 示例2：类型2 - 直接图片URL
    image_input = "https://randomuser.me/api/portraits/men/1.jpg"
    
    # 示例3：类型3 - 百度图片搜索URL（会自动提取实际图片URL）
    # image_input = "https://image.baidu.com/search/detail?adpicid=0&b_applid=9789573169742938504&bdtype=0&commodity=&copyright=&cs=1850186389%2C55921271&di=7565560840087142401&fr=click-pic&fromurl=http%253A%252F%252Fwww.duitang.com%252Fblog%252F%253Fid%253D1512294406&gsm=78&hd=&height=0&hot=&ic=&ie=utf-8&imgformat=&imgratio=&imgspn=0&is=0%2C0&isImgSet=&latest=&lid=&lm=&objurl=https%253A%252F%252Fc-ssl.dtstatic.com%252Fuploads%252Fblog%252F202402%252F07%252FV2SOZWG9Cmg0Vq2.thumb.1000_0.png&os=1037517498%2C2535813189&pd=image_content&pi=0&pn=91&rn=1&simid=1850186389%2C55921271&tn=baiduimagedetail&width=0&word=%E7%9C%9F%E4%BA%BA%E5%A4%B4%E5%83%8F&z="
    
    result = detector.check_avatar(image_input)
    
    # 输出结果
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # 判断结果
    if result["hasValidAvatar"]:
        print(f"\n✓ 检测到有效头像，共 {result['faceCount']} 张人脸")
        print(f"  图片类型: {result.get('imageType', 'unknown')}")
    else:
        print(f"\n✗ 未检测到有效头像: {result['message']}")
        print(f"  图片类型: {result.get('imageType', 'unknown')}")


if __name__ == "__main__":
    main()
