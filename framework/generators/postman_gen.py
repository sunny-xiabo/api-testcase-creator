# postman_gen.py - 用例转 Postman Collection 生成器
# 将测试用例转换为可导入 Postman 的 Collection JSON

import json
import uuid
from collections import defaultdict


class PostmanGenerator:
    """Postman Collection 生成器"""

    def generate(self, testcases: list[dict], collection_name: str = "API 测试",
                 base_url: str = "") -> dict:
        """
        生成 Postman Collection v2.1 JSON

        返回: dict (可直接 json.dumps 导出)
        """
        # 按 endpoint 分组
        grouped = defaultdict(list)
        for tc in testcases:
            endpoint = tc.get("endpoint", "unknown")
            grouped[endpoint].append(tc)

        # 构建 items
        items = []
        for endpoint, cases in grouped.items():
            # 用文件夹按 endpoint 分组
            folder_items = []
            for tc in cases:
                request_item = self._tc_to_request(tc, base_url)
                folder_items.append(request_item)

            # 提取 endpoint 名作为文件夹名
            ep_parts = endpoint.split(" ", 1)
            method = ep_parts[0] if len(ep_parts) > 1 else "GET"
            path = ep_parts[1] if len(ep_parts) > 1 else endpoint

            items.append({
                "name": endpoint,
                "item": folder_items,
            })

        # 构建 Collection
        collection = {
            "info": {
                "name": collection_name,
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
                "description": f"由 api-testcase-creator 自动生成，共 {len(testcases)} 条用例",
            },
            "item": items,
            "variable": [
                {
                    "key": "base_url",
                    "value": base_url or "http://localhost:8080",
                    "type": "string",
                },
                {
                    "key": "token",
                    "value": "",
                    "type": "string",
                },
            ],
            "auth": {
                "type": "bearer",
                "bearer": [
                    {
                        "key": "token",
                        "value": "{{token}}",
                        "type": "string",
                    }
                ],
            },
        }

        return collection

    def _tc_to_request(self, tc: dict, base_url: str) -> dict:
        """将单条用例转为 Postman 请求项"""
        request = tc.get("request", {})
        expected = tc.get("expected", {})
        tc_id = tc.get("id", "")
        test_point = tc.get("test_point", "")

        method = request.get("method", "GET")
        path = request.get("path", "/")
        body = request.get("body")
        query_params = request.get("query_params")
        headers = request.get("headers")
        path_params = request.get("path_params", {})

        path_variables = []
        for key, value in path_params.items():
            path = path.replace(f"{{{key}}}", f"{{{{{key}}}}}")
            path_variables.append({
                "key": key,
                "value": str(value),
            })

        path_parts = [p for p in path.split("/") if p]
        raw_url = f"{{{{base_url}}}}{path}"

        # URL
        url = {
            "raw": raw_url,
            "host": ["{{base_url}}"],
            "path": path_parts,
        }
        if path_variables:
            url["variable"] = path_variables

        # 查询参数
        if query_params:
            url["query"] = []
            for key, value in query_params.items():
                url["query"].append({
                    "key": key,
                    "value": str(value),
                    "description": "",
                })

        # Headers
        postman_headers = [
            {
                "key": "Content-Type",
                "value": "application/json",
            }
        ]
        if headers:
            for key, value in headers.items():
                postman_headers.append({
                    "key": key,
                    "value": str(value),
                })

        # 请求体
        postman_body = None
        if body:
            postman_body = {
                "mode": "raw",
                "raw": json.dumps(body, ensure_ascii=False, indent=2),
                "options": {
                    "raw": {
                        "language": "json",
                    }
                },
            }

        # 构建请求对象
        postman_request = {
            "method": method,
            "header": postman_headers,
            "url": url,
            "description": f"{tc_id}: {test_point}",
        }
        if postman_body:
            postman_request["body"] = postman_body

        # 如果有认证标记，添加 auth
        if tc.get("precondition", "").find("已登录") >= 0:
            postman_request["auth"] = {
                "type": "bearer",
                "bearer": [
                    {
                        "key": "token",
                        "value": "{{token}}",
                        "type": "string",
                    }
                ],
            }

        # 构建测试脚本（断言）
        expected_code = expected.get("status_code", 200)
        checks = expected.get("checks", [])

        test_script = [
            f"pm.test('状态码为 {expected_code}', function() {{",
            f"    pm.response.to.have.status({expected_code});",
            f"}});",
        ]

        for check in checks:
            if "包含" in check:
                import re
                match = re.search(r"'(.+?)'", check)
                if match:
                    keyword = match.group(1)
                    test_script.extend([
                        f"pm.test('响应包含 {keyword}', function() {{",
                        f"    pm.expect(pm.response.text()).to.include('{keyword}');",
                        f"}});",
                    ])
            elif "非空" in check:
                test_script.extend([
                    "pm.test('响应体非空', function() {",
                    "    pm.expect(pm.response.json()).to.be.an('object');",
                    "});",
                ])

        # 构建完整项
        item = {
            "name": f"{tc_id}: {test_point}",
            "request": postman_request,
            "event": [
                {
                    "listen": "test",
                    "script": {
                        "exec": test_script,
                    },
                }
            ],
        }

        return item

    def write(self, collection: dict, output_path: str):
        """将 Collection 写入文件"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(collection, f, ensure_ascii=False, indent=2)
