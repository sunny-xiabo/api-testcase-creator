# openapi_parser.py - OpenAPI 3.0 / Swagger 2.0 解析器
# 解析 JSON/YAML 格式的接口文档，输出统一的 Endpoint 列表

import json
import re
from typing import Any
from pathlib import Path
from .base import BaseParser
from .endpoint_model import Endpoint, Param, RequestBodyField, Response


class OpenAPIParser(BaseParser):
    """OpenAPI 3.0 解析器"""

    def __init__(self):
        self._spec = None
        self._components = {}

    def parse(self, file_path: str) -> list[Endpoint]:
        """解析 OpenAPI 3.0 JSON/YAML 文件"""
        content = self.read_file(file_path)
        path = Path(file_path)

        # 根据后缀选择解析方式
        if path.suffix in ('.yaml', '.yml'):
            import yaml
            self._spec = yaml.safe_load(content)
        else:
            self._spec = json.loads(content)

        # 检测版本
        openapi_version = self._spec.get('openapi', '')
        swagger_version = self._spec.get('swagger', '')

        if swagger_version.startswith('2'):
            # Swagger 2.0 先转成 3.0 结构再解析
            self._spec = self._convert_swagger2_to_openapi3(self._spec)

        # 缓存 components 用于 $ref 解引用
        self._components = self._spec.get('components', {})

        # 遍历 paths 解析每个接口
        endpoints = []
        paths = self._spec.get('paths', {})
        for path_str, path_item in paths.items():
            for method in ('get', 'post', 'put', 'delete', 'patch', 'head', 'options'):
                operation = path_item.get(method)
                if not operation:
                    continue
                endpoint = self._parse_operation(method, path_str, operation, path_item)
                endpoints.append(endpoint)

        return endpoints

    def _parse_operation(self, method: str, path: str, operation: dict, path_item: dict) -> Endpoint:
        """解析单个 operation"""
        # 参数
        parameters = self._parse_parameters(operation, path_item)

        # 请求体
        request_body = self._parse_request_body(operation.get('requestBody', {}))

        # 响应
        responses = self._parse_responses(operation.get('responses', {}))

        # 安全
        security = []
        op_security = operation.get('security', self._spec.get('security', []))
        for sec in op_security:
            security.extend(sec.keys())

        # 标签
        tags = operation.get('tags', [])

        return Endpoint(
            method=method.upper(),
            path=path,
            summary=operation.get('summary', ''),
            description=operation.get('description', ''),
            tags=tags,
            parameters=parameters,
            request_body=request_body,
            responses=responses,
            security=list(set(security)),
            deprecated=operation.get('deprecated', False),
        )

    def _parse_parameters(self, operation: dict, path_item: dict) -> list[Param]:
        """解析参数（path + operation 级别合并）"""
        params = []
        # 合并 path 级别和 operation 级别的参数
        raw_params = path_item.get('parameters', []) + operation.get('parameters', [])

        for p in raw_params:
            # 解引用
            p = self._resolve_ref(p)
            schema = p.get('schema', {})

            params.append(Param(
                name=p.get('name', ''),
                location=p.get('in', 'query'),
                type=schema.get('type', 'string'),
                required=p.get('required', False),
                description=p.get('description', ''),
                enum=schema.get('enum', []),
                minimum=schema.get('minimum'),
                maximum=schema.get('maximum'),
                min_length=schema.get('minLength'),
                max_length=schema.get('maxLength'),
                pattern=schema.get('pattern'),
                default=schema.get('default'),
                example=schema.get('example'),
            ))

        return params

    def _parse_request_body(self, request_body: dict) -> list[RequestBodyField]:
        """解析请求体"""
        if not request_body:
            return []

        # 解引用
        request_body = self._resolve_ref(request_body)

        # 取可用的 schema
        content = request_body.get('content', {})
        schema, _ = self._pick_content_schema(content)

        if not schema:
            return []

        # 解引用
        schema = self._resolve_ref(schema)

        # 解析 properties
        return self._schema_to_fields(schema, request_body)

    def _schema_to_fields(self, schema: dict, request_body: dict = None, prefix: str = "") -> list[RequestBodyField]:
        """将 JSON Schema 转为字段列表"""
        fields = []
        schema = self._resolve_ref(schema)

        # 合并组合类型
        for key in ('allOf', 'oneOf', 'anyOf'):
            if key in schema and isinstance(schema[key], list):
                for sub_schema in schema[key]:
                    fields.extend(self._schema_to_fields(self._resolve_ref(sub_schema), request_body, prefix))
                return self._dedupe_fields(fields)

        required_fields = set(schema.get('required', []))
        properties = schema.get('properties', {})

        for name, prop_schema in properties.items():
            prop_schema = self._resolve_ref(prop_schema)
            field_name = f"{prefix}.{name}" if prefix else name
            field_type = prop_schema.get('type', 'string')

            # 嵌套对象递归展开
            if field_type == 'object' and prop_schema.get('properties'):
                fields.extend(self._schema_to_fields(prop_schema, request_body, field_name))
                continue

            # 数组中包含对象时递归展开为 items[0].field
            if field_type == 'array':
                items_schema = self._resolve_ref(prop_schema.get('items', {}))
                if isinstance(items_schema, dict):
                    for key in ('allOf', 'oneOf', 'anyOf'):
                        if key in items_schema and isinstance(items_schema[key], list):
                            for sub_schema in items_schema[key]:
                                fields.extend(self._schema_to_fields(self._resolve_ref(sub_schema), request_body, f"{field_name}[0]"))
                            break
                    else:
                        if items_schema.get('type') == 'object' and items_schema.get('properties'):
                            fields.extend(self._schema_to_fields(items_schema, request_body, f"{field_name}[0]"))
                            continue

            fields.append(RequestBodyField(
                name=field_name,
                type=field_type,
                required=name in required_fields,
                description=prop_schema.get('description', ''),
                enum=prop_schema.get('enum', []),
                minimum=prop_schema.get('minimum'),
                maximum=prop_schema.get('maximum'),
                min_length=prop_schema.get('minLength'),
                max_length=prop_schema.get('maxLength'),
                pattern=prop_schema.get('pattern'),
                default=prop_schema.get('default'),
                example=prop_schema.get('example'),
            ))

        return self._dedupe_fields(fields)

    def _dedupe_fields(self, fields: list[RequestBodyField]) -> list[RequestBodyField]:
        """按字段名去重，保留首次出现的定义"""
        unique = []
        seen = set()
        for field in fields:
            if field.name in seen:
                continue
            seen.add(field.name)
            unique.append(field)
        return unique

    def _parse_responses(self, responses: dict) -> list[Response]:
        """解析响应定义"""
        result = []
        for status_code, resp in responses.items():
            resp = self._resolve_ref(resp)

            # 尝试提取可用的 schema
            schema = {}
            example = None
            content = resp.get('content', {})
            schema, example = self._pick_content_schema(content)

            # 将 schema 中的 $ref 解引用
            if schema:
                schema = self._deep_resolve(schema)

            try:
                code = int(status_code)
            except (ValueError, TypeError):
                code = 0  # 'default' 等非数字状态码

            result.append(Response(
                status_code=code,
                description=resp.get('description', ''),
                schema=schema,
                example=example,
            ))

        return result

    def _pick_content_schema(self, content: dict) -> tuple[dict, Any]:
        """从 content 中挑选最合适的 schema 和 example"""
        if not isinstance(content, dict):
            return {}, None

        preferred_types = (
            'application/json',
            'application/x-www-form-urlencoded',
            'multipart/form-data',
            'text/json',
        )

        candidates = list(preferred_types)
        candidates.extend([k for k in content.keys() if k not in candidates])

        for content_type in candidates:
            media = content.get(content_type, {})
            if not isinstance(media, dict):
                continue
            schema = media.get('schema', {})
            if schema:
                schema = self._resolve_ref(schema)
                example = media.get('example')
                if example is None and 'examples' in media and isinstance(media['examples'], dict):
                    first_example = next(iter(media['examples'].values()), {})
                    if isinstance(first_example, dict):
                        example = first_example.get('value')
                return schema, example

        return {}, None

    def _resolve_ref(self, obj: dict) -> dict:
        """解引用 $ref"""
        if not isinstance(obj, dict):
            return obj
        ref = obj.get('$ref')
        if not ref:
            return obj
        return self._follow_ref(ref)

    def _follow_ref(self, ref: str) -> dict:
        """根据 $ref 路径找到对应定义"""
        # #/components/schemas/User -> ['components', 'schemas', 'User']
        if not ref.startswith('#/'):
            return {}
        parts = ref[2:].split('/')
        current = self._spec
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part, {})
            else:
                return {}
        return current if isinstance(current, dict) else {}

    def _deep_resolve(self, schema: dict, depth: int = 10) -> dict:
        """深度解引用（防止循环引用）"""
        if depth <= 0 or not isinstance(schema, dict):
            return schema

        schema = self._resolve_ref(schema)

        # 递归处理 properties
        if 'properties' in schema:
            resolved_props = {}
            for k, v in schema['properties'].items():
                resolved_props[k] = self._deep_resolve(v, depth - 1)
            schema['properties'] = resolved_props

        # 递归处理 items (array)
        if 'items' in schema:
            schema['items'] = self._deep_resolve(schema['items'], depth - 1)

        # 递归处理 allOf/oneOf/anyOf
        for key in ('allOf', 'oneOf', 'anyOf'):
            if key in schema:
                schema[key] = [self._deep_resolve(s, depth - 1) for s in schema[key]]

        return schema

    def _convert_swagger2_to_openapi3(self, swagger: dict) -> dict:
        """将 Swagger 2.0 结构转换为 OpenAPI 3.0 兼容结构（简化版）"""
        openapi = {
            'openapi': '3.0.0',
            'info': swagger.get('info', {}),
            'paths': {},
            'components': {
                'schemas': swagger.get('definitions', {}),
                'parameters': {},
                'securitySchemes': {},
            },
            'security': [],
        }

        # 转换 securityDefinitions -> components.securitySchemes
        for name, scheme in swagger.get('securityDefinitions', {}).items():
            openapi['components']['securitySchemes'][name] = scheme

        # 全局 security
        if 'security' in swagger:
            openapi['security'] = swagger['security']

        # 转换 paths
        for path_str, path_item in swagger.get('paths', {}).items():
            new_path = {}
            # path 级别参数
            path_params = path_item.get('parameters', [])

            for method in ('get', 'post', 'put', 'delete', 'patch', 'head', 'options'):
                op = path_item.get(method)
                if not op:
                    continue

                # 合并参数
                all_params = path_params + op.get('parameters', [])

                # 分离 body 参数和其他参数
                query_params = []
                request_body = None
                form_data_fields = []  # 收集 formData 参数
                for p in all_params:
                    if p.get('in') == 'body':
                        request_body = {
                            'content': {
                                'application/json': {
                                    'schema': p.get('schema', {})
                                }
                            }
                        }
                    elif p.get('in') == 'formData':
                        # 收集 formData 参数，稍后统一处理
                        form_data_fields.append(p)
                    else:
                        # 转换 parameter 为 OpenAPI 3 格式
                        new_param = {
                            'name': p.get('name'),
                            'in': p.get('in'),
                            'required': p.get('required', False),
                            'description': p.get('description', ''),
                            'schema': p.get('schema', {'type': p.get('type', 'string')}),
                        }
                        query_params.append(new_param)

                # 转换 responses
                responses = {}
                for status, resp in op.get('responses', {}).items():
                    new_resp = {'description': resp.get('description', '')}
                    if 'schema' in resp:
                        new_resp['content'] = {
                            'application/json': {
                                'schema': resp['schema']
                            }
                        }
                    responses[status] = new_resp

                # 处理 formData 参数（如果有）
                if form_data_fields and not request_body:
                    # 将 formData 参数转换为请求体
                    properties = {}
                    required_fields = []
                    for p in form_data_fields:
                        field_name = p.get('name', '')
                        field_type = p.get('type', 'string')
                        properties[field_name] = {'type': field_type}
                        if p.get('required', False):
                            required_fields.append(field_name)

                    schema = {'type': 'object', 'properties': properties}
                    if required_fields:
                        schema['required'] = required_fields

                    # 检查是否有文件类型参数
                    has_file = any(p.get('type') == 'file' for p in form_data_fields)
                    content_type = 'multipart/form-data' if has_file else 'application/x-www-form-urlencoded'

                    request_body = {
                        'content': {
                            content_type: {
                                'schema': schema
                            }
                        }
                    }

                new_op = {
                    'summary': op.get('summary', ''),
                    'description': op.get('description', ''),
                    'tags': op.get('tags', []),
                    'parameters': query_params,
                    'responses': responses,
                    'deprecated': op.get('deprecated', False),
                }
                if request_body:
                    new_op['requestBody'] = request_body
                if 'security' in op:
                    new_op['security'] = op['security']

                new_path[method] = new_op

            openapi['paths'][path_str] = new_path

        return openapi
