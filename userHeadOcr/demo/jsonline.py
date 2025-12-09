"""
JSONL 格式数据读写工具
支持全量读取、新增、修改、删除操作，数据按 id 升序排序
"""
import json
import os
from typing import List, Dict, Any, Optional
from pathlib import Path


class JsonLineDB:
    """JSONL 格式数据库操作类"""
    
    def __init__(self, db_path: str):
        """
        初始化数据库连接
        
        Args:
            db_path: 数据库文件路径（相对于项目根目录或绝对路径）
        """
        # 转换为 Path 对象以便处理路径
        self.db_path = Path(db_path)
        # 确保目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _read_all_lines(self) -> List[Dict[str, Any]]:
        """
        读取所有数据行
        
        Returns:
            包含所有 JSON 对象的列表
        """
        if not self.db_path.exists():
            return []
        
        data_list = []
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:  # 跳过空行
                        try:
                            data_list.append(json.loads(line))
                        except json.JSONDecodeError as e:
                            print(f"解析 JSON 行时出错: {e}, 行内容: {line[:50]}...")
                            continue
        except Exception as e:
            print(f"读取文件时出错: {e}")
            raise
        
        return data_list
    
    def _write_all_lines(self, data_list: List[Dict[str, Any]]) -> bool:
        """
        将所有数据写入文件（按 id 升序排序）
        
        Args:
            data_list: 要写入的数据列表
            
        Returns:
            是否写入成功
        """
        try:
            # 按 id 升序排序
            sorted_data = sorted(data_list, key=lambda x: x.get('id', 0))
            
            # 使用临时文件写入，确保原子性
            temp_path = self.db_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                for item in sorted_data:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')
            
            # 替换原文件
            if self.db_path.exists():
                os.replace(temp_path, self.db_path)
            else:
                temp_path.rename(self.db_path)
            
            return True
        except Exception as e:
            print(f"写入文件时出错: {e}")
            # 清理临时文件
            if temp_path.exists():
                temp_path.unlink()
            return False
    
    def read_all(self) -> List[Dict[str, Any]]:
        """
        全量读取所有数据
        
        Returns:
            所有数据行的列表，按 id 升序排序
        """
        data_list = self._read_all_lines()
        # 确保按 id 升序排序
        return sorted(data_list, key=lambda x: x.get('id', 0))
    
    def upsert(self, data: Dict[str, Any], id_key: str = 'id') -> bool:
        """
        新增或修改数据（如果 id 存在则更新，否则新增）
        
        Args:
            data: 要插入或更新的数据字典，必须包含 id 字段
            id_key: id 字段的键名，默认为 'id'
            
        Returns:
            是否操作成功
            
        Raises:
            ValueError: 如果数据中不包含 id 字段
        """
        if id_key not in data:
            raise ValueError(f"数据中必须包含 '{id_key}' 字段")
        
        data_id = data[id_key]
        data_list = self._read_all_lines()
        
        # 查找是否存在相同 id 的记录
        found = False
        for i, item in enumerate(data_list):
            if item.get(id_key) == data_id:
                # 更新现有记录
                data_list[i] = data
                found = True
                break
        
        # 如果不存在，则新增
        if not found:
            data_list.append(data)
        
        # 写入文件（会自动排序）
        return self._write_all_lines(data_list)
    
    def delete(self, data_id: Any, id_key: str = 'id') -> bool:
        """
        根据 id 删除数据
        
        Args:
            data_id: 要删除的数据的 id 值
            id_key: id 字段的键名，默认为 'id'
            
        Returns:
            是否删除成功（如果 id 不存在也返回 True，表示操作完成）
        """
        data_list = self._read_all_lines()
        
        # 过滤掉指定 id 的记录
        original_count = len(data_list)
        data_list = [item for item in data_list if item.get(id_key) != data_id]
        
        # 如果删除了记录，则写入文件
        if len(data_list) < original_count:
            return self._write_all_lines(data_list)
        else:
            # 没有找到要删除的记录，但操作也算成功
            return True
    
    def get_by_id(self, data_id: Any, id_key: str = 'id') -> Optional[Dict[str, Any]]:
        """
        根据 id 获取单条数据
        
        Args:
            data_id: 要查询的数据的 id 值
            id_key: id 字段的键名，默认为 'id'
            
        Returns:
            找到的数据字典，如果不存在则返回 None
        """
        data_list = self._read_all_lines()
        for item in data_list:
            if item.get(id_key) == data_id:
                return item
        return None
    
    def exists(self, data_id: Any, id_key: str = 'id') -> bool:
        """
        检查指定 id 的数据是否存在
        
        Args:
            data_id: 要检查的数据的 id 值
            id_key: id 字段的键名，默认为 'id'
            
        Returns:
            如果存在返回 True，否则返回 False
        """
        return self.get_by_id(data_id, id_key) is not None


# 便捷函数：创建默认的数据库实例
_default_db: Optional[JsonLineDB] = None

def get_db(db_path: str = None) -> JsonLineDB:
    """
    获取数据库实例（单例模式）
    
    Args:
        db_path: 数据库文件路径，如果为 None 则使用默认路径
        
    Returns:
        JsonLineDB 实例
    """
    global _default_db
    if db_path is None:
        # 默认路径：相对于当前文件所在目录
        script_dir = Path(__file__).parent.absolute()
        db_path = script_dir / "data" / "db.json"
    
    if _default_db is None or str(_default_db.db_path) != str(db_path):
        _default_db = JsonLineDB(str(db_path))
    
    return _default_db


# 示例用法
if __name__ == "__main__":
    # 创建数据库实例
    db = get_db()
    
    # 测试数据
    test_data = [
        {"id": 3, "name": "张三", "age": 25},
        {"id": 1, "name": "李四", "age": 30},
        {"id": 2, "name": "王五", "age": 28},
    ]
    
    print("=== 测试新增数据 ===")
    for data in test_data:
        db.upsert(data)
        print(f"新增/更新: {data}")
    
    print("\n=== 全量读取（应该按 id 升序） ===")
    all_data = db.read_all()
    for item in all_data:
        print(item)
    
    print("\n=== 测试修改数据（更新 id=2 的记录） ===")
    db.upsert({"id": 2, "name": "王五（已更新）", "age": 29})
    print("更新后的数据：")
    all_data = db.read_all()
    for item in all_data:
        print(item)
    
    print("\n=== 测试删除数据（删除 id=1 的记录） ===")
    db.delete(1)
    print("删除后的数据：")
    all_data = db.read_all()
    for item in all_data:
        print(item)
    
    print("\n=== 测试根据 id 查询 ===")
    item = db.get_by_id(2)
    print(f"id=2 的记录: {item}")
