# base_case_gen.py - 程序化基础用例生成器
# 从 Endpoint 列表自动生成基础测试用例（不需要 LLM）

import copy
import itertools
import re
from ..parsers.endpoint_model import Endpoint, Param, RequestBodyField


class BaseCaseGenerator:
    """基础测试用例生成器"""

    def __init__(self):
        self._counter = 0

    def generate(self, endpoints: list[Endpoint]) -> list[dict]:
        """为所有接口生成基础测试用例"""
        all_cases = []
        for endpoint in endpoints:
            cases = self._generate_for_endpoint(endpoint)
            all_cases.extend(cases)
        return all_cases

    def _next_id(self) -> str:
        """生成下一个用例 ID"""
        self._counter += 1
        return f"TC-{self._counter:03d}"

    def _generate_for_endpoint(self, ep: Endpoint) -> list[dict]:
        """为单个接口生成所有基础用例"""
        cases = []

        # 1. 正向用例
        cases.extend(self._positive_cases(ep))

        # 2. 必填参数缺失
        cases.extend(self._missing_required_cases(ep))

        # 3. 参数类型错误
        cases.extend(self._wrong_type_cases(ep))

        # 4. 边界值
        cases.extend(self._boundary_cases(ep))

        # 5. 枚举值
        cases.extend(self._enum_cases(ep))

        # 6. 认证测试
        if ep.has_auth:
            cases.extend(self._auth_cases(ep))

        return cases

    def _build_request(self, ep: Endpoint, body_override: dict = None,
                       param_override: dict = None, headers_override: dict = None,
                       exclude_params: set = None) -> dict:
        """构建请求描述"""
        exclude_params = exclude_params or set()
        request = {
            "method": ep.method,
            "path": ep.path,
        }

        # 构建路径参数
        path_params = {}
        for p in ep.parameters:
            if p.location == 'path':
                if param_override and p.name in param_override:
                    path_params[p.name] = param_override[p.name]
                else:
                    path_params[p.name] = self._sample_value_from_param(p)
        if path_params:
            request["path_params"] = path_params

        # 构建合法的请求体
        if ep.request_body and body_override is None:
            body = {}
            for field in ep.request_body:
                self._set_nested_value(body, field.name, self._sample_value(field))
            request["body"] = body
        elif body_override is not None:
            request["body"] = body_override

        # 构建查询参数
        if ep.parameters:
            params = {}
            for p in ep.parameters:
                if p.location == 'query' and p.name not in exclude_params:
                    if param_override and p.name in param_override:
                        params[p.name] = param_override[p.name]
                    elif p.required:
                        params[p.name] = self._sample_value_from_param(p)
            if params:
                request["query_params"] = params

        # Headers
        if headers_override:
            request["headers"] = headers_override

        return request

    def _set_nested_value(self, target: dict, dotted_name: str, value) -> None:
        """按 dotted path 写入嵌套值"""
        parts = []
        for segment in dotted_name.split("."):
            parts.extend([token for token in re.split(r"(\[\d+\])", segment) if token])

        def normalize(token):
            if token.startswith("[") and token.endswith("]"):
                return int(token[1:-1])
            return token

        tokens = [normalize(part) for part in parts]

        def assign(container, path):
            head = path[0]
            if len(path) == 1:
                if isinstance(head, int):
                    while len(container) <= head:
                        container.append(None)
                    container[head] = value
                else:
                    container[head] = value
                return

            tail = path[1]
            if isinstance(head, int):
                while len(container) <= head:
                    container.append([] if isinstance(tail, int) else {})
                if container[head] is None or not isinstance(container[head], (dict, list)):
                    container[head] = [] if isinstance(tail, int) else {}
                assign(container[head], path[1:])
                return

            if head not in container or not isinstance(container[head], (dict, list)):
                container[head] = [] if isinstance(tail, int) else {}
            assign(container[head], path[1:])

        assign(target, tokens)

    def _sample_value(self, field) -> any:
        """根据字段类型生成示例值"""
        if field.example is not None:
            return field.example
        if field.default is not None:
            return field.default
        if field.enum:
            return field.enum[0]

        type_map = {
            "string": "test_string",
            "integer": 1,
            "number": 1.0,
            "boolean": True,
            "array": [],
            "object": {},
        }
        return type_map.get(field.type, "test_value")

    def _sample_value_from_param(self, p: Param) -> any:
        """根据参数定义生成示例值"""
        if p.example is not None:
            return p.example
        if p.default is not None:
            return p.default
        if p.enum:
            return p.enum[0]

        type_map = {
            "string": "test_value",
            "integer": 1,
            "number": 1.0,
            "boolean": True,
        }
        return type_map.get(p.type, "test_value")

    def _wrong_value(self, field) -> any:
        """根据字段类型生成错误类型的值"""
        type_wrong = {
            "string": 12345,           # string 给 int
            "integer": "not_a_number", # int 给 string
            "number": "not_a_number",  # number 给 string
            "boolean": "not_bool",     # bool 给 string
            "array": "not_array",      # array 给 string
            "object": "not_object",    # object 给 string
        }
        return type_wrong.get(field.type, None)

    # ---- 正向用例 ----

    def _positive_cases(self, ep: Endpoint) -> list[dict]:
        """生成正向用例"""
        request = self._build_request(ep)

        # 找到成功响应码
        success_responses = [r for r in ep.responses if 200 <= r.status_code < 300]
        expected_code = success_responses[0].status_code if success_responses else 200

        checks = []
        if expected_code == 200:
            checks.append("状态码为 200")
        if expected_code != 204 and success_responses:
            checks.append("响应体非空")

            response_schema = success_responses[0].schema or {}
            response_example = success_responses[0].example or {}
            response_keys = []
            if isinstance(response_example, dict):
                response_keys.extend(response_example.keys())
            if isinstance(response_schema, dict):
                response_keys.extend((response_schema.get("properties") or {}).keys())

            for key in list(dict.fromkeys(response_keys))[:3]:
                checks.append(f"响应包含 '{key}'")

        return [{
            "id": self._next_id(),
            "endpoint": ep.full_path,
            "test_point": f"正向调用 {ep.summary or ep.full_path}",
            "request": request,
            "precondition": "已登录，持有有效 token" if ep.has_auth else "无",
            "expected": {"status_code": expected_code, "checks": checks},
            "checkpoint": "API-BASIC",
            "scene_type": "正向",
            "priority": "P0",
        }]

    # ---- 必填参数缺失 ----

    def _missing_required_cases(self, ep: Endpoint) -> list[dict]:
        """为每个必填参数生成缺失测试用例"""
        cases = []

        # 请求体必填字段
        for field in ep.required_body_fields:
            body = {}
            for f in ep.request_body:
                if f.name != field.name:
                    self._set_nested_value(body, f.name, self._sample_value(f))
            request = self._build_request(ep, body_override=body)

            cases.append({
                "id": self._next_id(),
                "endpoint": ep.full_path,
                "test_point": f"缺少必填参数 {field.name}",
                "request": request,
                "precondition": "已登录，持有有效 token" if ep.has_auth else "无",
                "expected": {"status_code": 400, "checks": [f"错误信息包含 '{field.name}'"]},
                "checkpoint": "API-001",
                "scene_type": "异常",
                "priority": "P0",
            })

        # 查询参数必填字段
        for p in ep.parameters:
            if p.required and p.location == 'query':
                # 构建不含该参数的请求
                request = self._build_request(ep, exclude_params={p.name})

                cases.append({
                    "id": self._next_id(),
                    "endpoint": ep.full_path,
                    "test_point": f"缺少必填查询参数 {p.name}",
                    "request": request,
                    "precondition": "已登录，持有有效 token" if ep.has_auth else "无",
                    "expected": {"status_code": 400, "checks": [f"错误信息包含 '{p.name}'"]},
                    "checkpoint": "API-001",
                    "scene_type": "异常",
                    "priority": "P0",
                })

        return cases

    # ---- 参数类型错误 ----

    def _wrong_type_cases(self, ep: Endpoint) -> list[dict]:
        """为每个字段生成类型错误测试用例"""
        cases = []

        for field in ep.request_body:
            wrong_val = self._wrong_value(field)
            if wrong_val is None:
                continue

            body = {}
            for f in ep.request_body:
                if f.name == field.name:
                    self._set_nested_value(body, f.name, wrong_val)
                else:
                    self._set_nested_value(body, f.name, self._sample_value(f))

            request = self._build_request(ep, body_override=body)
            cases.append({
                "id": self._next_id(),
                "endpoint": ep.full_path,
                "test_point": f"参数 {field.name} 类型错误（{field.type} 填 {type(wrong_val).__name__}）",
                "request": request,
                "precondition": "已登录，持有有效 token" if ep.has_auth else "无",
                "expected": {"status_code": 400, "checks": [f"错误信息包含 '{field.name}'"]},
                "checkpoint": "API-002",
                "scene_type": "异常",
                "priority": "P0",
            })

        return cases

    # ---- 边界值 ----

    def _boundary_cases(self, ep: Endpoint) -> list[dict]:
        """为有约束的字段生成边界值测试用例"""
        cases = []

        for field in ep.request_body:
            boundaries = self._get_boundaries(field)
            for boundary_name, boundary_value in boundaries:
                body = {}
                for f in ep.request_body:
                    if f.name == field.name:
                        self._set_nested_value(body, f.name, boundary_value)
                    else:
                        self._set_nested_value(body, f.name, self._sample_value(f))

                request = self._build_request(ep, body_override=body)

                # 判断预期：合法边界应该成功，非法边界应该失败
                is_valid = boundary_name.startswith("min_") or boundary_name.startswith("max_")
                if "exceed" in boundary_name or "below" in boundary_name:
                    is_valid = False

                expected_code = 200 if is_valid else 400
                cases.append({
                    "id": self._next_id(),
                    "endpoint": ep.full_path,
                    "test_point": f"{field.name} 边界值: {boundary_name} = {boundary_value}",
                    "request": request,
                    "precondition": "已登录，持有有效 token" if ep.has_auth else "无",
                    "expected": {"status_code": expected_code, "checks": []},
                    "checkpoint": "API-003",
                    "scene_type": "边界",
                    "priority": "P1",
                })

        return cases

    def _get_boundaries(self, field) -> list[tuple]:
        """获取字段的边界值列表"""
        boundaries = []

        # 数值边界
        if field.type in ('integer', 'number'):
            if field.minimum is not None:
                boundaries.append(("min_value", field.minimum))
                if field.minimum > 0:
                    boundaries.append(("below_min", field.minimum - 1))
            if field.maximum is not None:
                boundaries.append(("max_value", field.maximum))
                boundaries.append(("exceed_max", field.maximum + 1))

        # 字符串长度边界
        if field.type == 'string':
            if field.min_length is not None:
                boundaries.append(("min_length", "a" * field.min_length))
                if field.min_length > 0:
                    boundaries.append(("below_min_length", "a" * (field.min_length - 1)))
            if field.max_length is not None:
                boundaries.append(("max_length", "a" * field.max_length))
                boundaries.append(("exceed_max_length", "a" * (field.max_length + 1)))

        return boundaries

    # ---- 枚举值 ----

    def _enum_cases(self, ep: Endpoint) -> list[dict]:
        """为有枚举的字段生成枚举值测试用例"""
        cases = []

        for field in ep.request_body:
            if not field.enum:
                continue

            # 测试非法枚举值
            body = {}
            for f in ep.request_body:
                if f.name == field.name:
                    self._set_nested_value(body, f.name, "INVALID_ENUM_VALUE_12345")
                else:
                    self._set_nested_value(body, f.name, self._sample_value(f))

            request = self._build_request(ep, body_override=body)
            cases.append({
                "id": self._next_id(),
                "endpoint": ep.full_path,
                "test_point": f"{field.name} 非法枚举值",
                "request": request,
                "precondition": "已登录，持有有效 token" if ep.has_auth else "无",
                "expected": {"status_code": 400, "checks": [f"错误信息包含 '{field.name}'"]},
                "checkpoint": "API-003",
                "scene_type": "异常",
                "priority": "P1",
            })

        return cases

    # ---- 认证测试 ----

    def _auth_cases(self, ep: Endpoint) -> list[dict]:
        """生成认证相关测试用例"""
        cases = []
        request = self._build_request(ep)

        # 无 token（使用深拷贝避免修改原始 request）
        no_auth_request = copy.deepcopy(request)
        no_auth_request["headers"] = {"Authorization": ""}
        cases.append({
            "id": self._next_id(),
            "endpoint": ep.full_path,
            "test_point": "无 Token 访问需认证接口",
            "request": no_auth_request,
            "precondition": "未登录",
            "expected": {"status_code": 401, "checks": ["返回 401 未授权"]},
            "checkpoint": "API-AUTH-001",
            "scene_type": "异常",
            "priority": "P0",
        })

        # 错误 token（使用深拷贝避免修改原始 request）
        bad_auth_request = copy.deepcopy(request)
        bad_auth_request["headers"] = {"Authorization": "Bearer invalid_token_12345"}
        cases.append({
            "id": self._next_id(),
            "endpoint": ep.full_path,
            "test_point": "伪造 Token 访问需认证接口",
            "request": bad_auth_request,
            "precondition": "持有伪造 token",
            "expected": {"status_code": 401, "checks": ["返回 401 未授权"]},
            "checkpoint": "API-AUTH-003",
            "scene_type": "异常",
            "priority": "P0",
        })

        return cases
