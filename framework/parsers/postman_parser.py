# postman_parser.py - Postman Collection v2.1 解析器
# 解析 Postman Collection JSON 文件，输出统一的 Endpoint 列表

import json
import re
from .base import BaseParser
from .endpoint_model import Endpoint, Param, RequestBodyField, Response


class PostmanParser(BaseParser):
    """Postman Collection v2.1 解析器"""

    def parse(self, file_path: str) -> list[Endpoint]:
        """解析 Postman Collection JSON 文件"""
        content = self.read_file(file_path)
        collection = json.loads(content)

        # 验证格式
        info = collection.get('info', {})
        schema = info.get('schema', '')
        if 'v2.1' not in schema and 'v2.0' not in schema:
            print(f"[WARN] 非标准 Postman Collection v2.x 格式，尝试解析...")

        # 遍历 items 解析接口
        endpoints = []
        items = collection.get('item', [])
        self._parse_items(items, endpoints)

        return endpoints

    def _parse_items(self, items: list, endpoints: list, folder_tags: list = None):
        """递归解析 items（Postman 支持文件夹嵌套）"""
        folder_tags = folder_tags or []

        for item in items:
            # 如果是文件夹（有 item 子项）
            if 'item' in item:
                folder_name = item.get('name', '')
                self._parse_items(item['item'], endpoints, folder_tags + [folder_name])
                continue

            # 如果是请求
            if 'request' in item:
                endpoint = self._parse_request(item, folder_tags)
                if endpoint:
                    endpoints.append(endpoint)

    def _parse_request(self, item: dict, folder_tags: list) -> Endpoint | None:
        """解析单个请求"""
        request = item.get('request', {})
        if not request:
            return None

        # 方法
        method = request.get('method', 'GET').upper()

        # URL
        url = request.get('url', {})
        if isinstance(url, str):
            path = url
            query_params = []
        else:
            # 构建路径
            raw = url.get('raw', '')
            path_parts = url.get('path', [])
            path = '/' + '/'.join(path_parts) if path_parts else raw

            # 提取路径参数
            path_params = []
            for part in path_parts:
                if part.startswith(':'):
                    path_params.append(Param(
                        name=part[1:],
                        location='path',
                        type='string',
                        required=True,
                    ))

            # 查询参数
            query_params = []
            for q in url.get('query', []):
                if q.get('disabled'):
                    continue
                query_params.append(Param(
                    name=q.get('key', ''),
                    location='query',
                    type='string',  # Postman 不声明类型
                    required=False,
                    description=q.get('description', ''),
                    example=q.get('value', ''),
                ))

        # 路径参数（从 :param 格式转为 {param} 格式）
        path = re.sub(r':(\w+)', r'{\1}', path)

        # 请求体
        request_body = []
        body = request.get('body', {})
        if body:
            mode = body.get('mode', '')
            if mode == 'raw':
                raw_body = body.get('raw', '')
                try:
                    body_json = json.loads(raw_body)
                    if isinstance(body_json, dict):
                        for key, value in body_json.items():
                            request_body.append(RequestBodyField(
                                name=key,
                                type=self._infer_type(value),
                                required=True,  # Postman 不声明 required，假设都 required
                                example=value,
                            ))
                except json.JSONDecodeError:
                    pass
            elif mode == 'urlencoded':
                for param in body.get('urlencoded', []):
                    if param.get('disabled'):
                        continue
                    request_body.append(RequestBodyField(
                        name=param.get('key', ''),
                        type='string',
                        required=not param.get('disabled', False),
                        example=param.get('value', ''),
                    ))

        # Headers
        headers = {}
        for header in request.get('header', []):
            if header.get('disabled'):
                continue
            headers[header.get('key', '')] = header.get('value', '')

        # 认证
        security = []
        auth = request.get('auth', {})
        if auth:
            auth_type = auth.get('type', '')
            if auth_type in ('bearer', 'oauth2', 'apikey'):
                security.append(auth_type)
            elif auth_type == 'basic':
                security.append('basic')

        # 也检查 header 中的 Authorization
        if not security:
            for header in request.get('header', []):
                if header.get('key', '').lower() == 'authorization':
                    security.append('bearer')
                    break

        # 标签：用文件夹名作为标签
        tags = folder_tags.copy()
        item_name = item.get('name', '')
        if item_name:
            tags.append(item_name)

        # 响应示例
        responses = []
        for resp in item.get('response', []):
            code = resp.get('code', 200)
            try:
                code = int(code)
            except (ValueError, TypeError):
                code = 200

            # 尝试从响应体推断 schema
            resp_body = resp.get('body', '')
            schema = {}
            example = None
            if resp_body:
                try:
                    example = json.loads(resp_body)
                except json.JSONDecodeError:
                    pass

            responses.append(Response(
                status_code=code,
                description=resp.get('name', ''),
                schema=schema,
                example=example,
            ))

        # 如果没有响应示例，添加默认的
        if not responses:
            responses = [
                Response(status_code=200, description="成功"),
                Response(status_code=400, description="参数错误"),
                Response(status_code=401, description="未授权"),
            ]

        # 合并路径参数到 parameters
        all_params = query_params.copy()
        for part in (url.get('path', []) if isinstance(url, dict) else []):
            if part.startswith(':'):
                all_params.append(Param(
                    name=part[1:],
                    location='path',
                    type='string',
                    required=True,
                ))

        return Endpoint(
            method=method,
            path=path,
            summary=item_name,
            description=request.get('description', '') if isinstance(request.get('description'), str) else request.get('description', {}).get('content', ''),
            tags=tags,
            parameters=all_params,
            request_body=request_body,
            responses=responses,
            security=security,
        )

    def _infer_type(self, value) -> str:
        """从值推断类型"""
        if isinstance(value, bool):
            return 'boolean'
        if isinstance(value, int):
            return 'integer'
        if isinstance(value, float):
            return 'number'
        if isinstance(value, list):
            return 'array'
        if isinstance(value, dict):
            return 'object'
        return 'string'
