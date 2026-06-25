# endpoint_model.py - 统一接口数据模型
# 所有 parser 的输出都统一为这个模型

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Param:
    """接口参数定义"""
    name: str                      # 参数名
    location: str                  # path / query / header / cookie
    type: str                      # string / integer / number / boolean / array / object
    required: bool = False
    description: str = ""
    enum: list = field(default_factory=list)
    minimum: float | None = None
    maximum: float | None = None
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None
    default: Any = None
    example: Any = None


@dataclass
class RequestBodyField:
    """请求体字段定义"""
    name: str                      # 字段名
    type: str                      # string / integer / number / boolean / array / object
    required: bool = False
    description: str = ""
    enum: list = field(default_factory=list)
    minimum: float | None = None
    maximum: float | None = None
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None
    default: Any = None
    example: Any = None


@dataclass
class Response:
    """响应定义"""
    status_code: int               # 200 / 400 / 401 / 404 / 500 ...
    description: str = ""
    schema: dict = field(default_factory=dict)     # JSON Schema
    example: dict | None = None


@dataclass
class Endpoint:
    """接口定义"""
    method: str                    # GET / POST / PUT / DELETE / PATCH
    path: str                      # /api/orders/{id}
    summary: str = ""              # 简要说明
    description: str = ""          # 详细描述
    tags: list = field(default_factory=list)       # 模块分组
    parameters: list = field(default_factory=list) # path/query/header 参数
    request_body: list = field(default_factory=list)  # 请求体字段列表
    responses: list = field(default_factory=list)  # 响应列表
    security: list = field(default_factory=list)   # 认证方式
    deprecated: bool = False

    @property
    def full_path(self) -> str:
        """返回完整标识: METHOD /path"""
        return f"{self.method.upper()} {self.path}"

    @property
    def has_auth(self) -> bool:
        """是否需要认证"""
        return len(self.security) > 0

    @property
    def required_body_fields(self) -> list:
        """返回请求体中必填字段"""
        return [f for f in self.request_body if f.required]

    @property
    def optional_body_fields(self) -> list:
        """返回请求体中可选字段"""
        return [f for f in self.request_body if not f.required]
