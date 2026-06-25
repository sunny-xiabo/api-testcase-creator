# base.py - 解析器基类

from abc import ABC, abstractmethod
from pathlib import Path
from .endpoint_model import Endpoint


class BaseParser(ABC):
    """接口文档解析器基类"""

    @abstractmethod
    def parse(self, file_path: str) -> list[Endpoint]:
        """解析接口文档文件，返回 Endpoint 列表"""
        pass

    @staticmethod
    def read_file(file_path: str) -> str:
        """读取文件内容"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
