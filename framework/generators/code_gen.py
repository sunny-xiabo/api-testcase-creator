# code_gen.py - 用例转 pytest 代码生成器
# 将结构化用例数据转换为可执行的 pytest 测试代码

import os
import re
import json
import textwrap
from collections import defaultdict


class CodeGenerator:
    """pytest 代码生成器"""

    def __init__(self, output_dir: str = "./tests"):
        self.output_dir = output_dir

    def generate(self, testcases: list[dict], project_name: str = "API",
                 base_url: str = "", module_name: str = "") -> dict:
        """
        生成完整的 pytest 项目结构

        返回: {"test_files": {...}, "conftest": str, "api_client": str, "config": str, "requirements": str}
        """
        # 按文件名分组（同 path 不同 method 放同一个文件）
        file_groups = self._group_by_file(testcases)

        # 生成文件
        result = {
            "test_files": {},
            "conftest": self._gen_conftest(testcases),
            "api_client": self._gen_api_client(),
            "config": self._gen_config(project_name, base_url),
            "requirements": self._gen_requirements(),
        }

        # 每个文件组生成一个 test 文件
        for filename, endpoint_cases in file_groups.items():
            content = self._gen_test_file(filename, endpoint_cases)
            result["test_files"][filename] = content

        return result

    def write_files(self, result: dict):
        """将生成结果写入文件系统"""
        os.makedirs(self.output_dir, exist_ok=True)

        # 写入 test 文件
        for filename, content in result["test_files"].items():
            filepath = os.path.join(self.output_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

        # 写入 conftest.py
        with open(os.path.join(self.output_dir, "conftest.py"), 'w', encoding='utf-8') as f:
            f.write(result["conftest"])

        # 写入 api_client.py
        with open(os.path.join(self.output_dir, "api_client.py"), 'w', encoding='utf-8') as f:
            f.write(result["api_client"])

        # 写入 config.yaml
        with open(os.path.join(self.output_dir, "config.yaml"), 'w', encoding='utf-8') as f:
            f.write(result["config"])

        # 写入 requirements.txt
        with open(os.path.join(self.output_dir, "requirements.txt"), 'w', encoding='utf-8') as f:
            f.write(result["requirements"])

    def _group_by_file(self, testcases: list[dict]) -> dict:
        """
        按输出文件名分组。
        同 path 不同 method 的用例放在同一个文件中。
        返回: {filename: {endpoint: [cases]}}
        """
        # 先按 endpoint 分组
        endpoint_groups = defaultdict(list)
        for tc in testcases:
            endpoint = tc.get("endpoint", "unknown")
            endpoint_groups[endpoint].append(tc)

        # 再按文件名分组
        file_groups = defaultdict(dict)
        for endpoint, cases in endpoint_groups.items():
            filename = self._endpoint_to_filename(endpoint)
            file_groups[filename][endpoint] = cases

        return dict(file_groups)

    def _endpoint_to_filename(self, endpoint: str) -> str:
        """将 endpoint 转为安全的文件名"""
        # "POST /api/orders" -> "test_api_orders.py"
        # "GET /api/orders/{id}" -> "test_api_orders.py" (同文件)
        path = endpoint.split(" ", 1)[-1] if " " in endpoint else endpoint
        # 去掉前缀 /api/ 等，去掉 {id} 等路径参数
        parts = [p for p in path.split("/") if p and not p.startswith("{")]
        name = "_".join(parts[-2:]) if len(parts) >= 2 else "_".join(parts)
        # 清理非法字符
        name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        name = re.sub(r'_+', '_', name).strip('_')
        return f"test_{name or 'api'}.py"

    def _gen_test_file(self, filename: str, endpoint_cases: dict) -> str:
        """
        生成单个测试文件，包含多个 endpoint 的类。

        endpoint_cases: {endpoint_str: [cases]}
        """
        # 收集所有用例确定模块 docstring
        all_cases = []
        for cases in endpoint_cases.values():
            all_cases.extend(cases)

        # 提取模块名（从第一个 endpoint 的 tags）
        first_ep = list(endpoint_cases.keys())[0]
        module_doc = f"{filename.replace('test_', '').replace('.py', '')} 模块接口自动化测试"

        lines = [
            '# -*- coding: utf-8 -*-',
            f'"""{module_doc}"""',
            '',
            'import pytest',
            'import json',
            'from api_client import ApiClient',
            '',
        ]

        # 每个 endpoint 生成一个 class
        for endpoint, cases in endpoint_cases.items():
            class_name = self._endpoint_to_class_name(endpoint)
            lines.append('')
            lines.append(f'class Test{class_name}:')
            lines.append(f'    """{endpoint} 接口测试"""')
            lines.append('')

            # 生成测试方法
            method_names = set()
            for tc in cases:
                method_code = self._gen_test_method(tc, method_names)
                for line in method_code.split('\n'):
                    lines.append(f'    {line}')
                lines.append('')

        return '\n'.join(lines) + '\n'

    def _endpoint_to_class_name(self, endpoint: str) -> str:
        """将 endpoint 转为类名，包含 method"""
        # "POST /api/orders" -> "PostOrders"
        # "GET /api/orders/{id}" -> "GetOrdersDetail"
        parts = endpoint.split(" ", 1)
        method = parts[0].capitalize() if len(parts) > 1 else "Get"
        path = parts[1] if len(parts) > 1 else endpoint

        # 提取路径部分，{id} 变为 Detail
        segments = []
        for p in path.split("/"):
            if not p:
                continue
            if p.startswith("{"):
                segments.append("Detail")
            else:
                segments.append(p.capitalize())

        name = "".join(segments[-3:]) if len(segments) >= 3 else "".join(segments)
        return f"{method}{name}" or "Api"

    def _gen_test_method(self, tc: dict, existing_names: set) -> str:
        """生成单个测试方法，确保方法名唯一"""
        method_name = self._tc_to_unique_method_name(tc, existing_names)
        existing_names.add(method_name)

        request = tc.get("request", {})
        expected = tc.get("expected", {})
        http_method = request.get("method", "POST").lower()
        path = request.get("path", "/")
        body = request.get("body")
        query_params = request.get("query_params")
        headers = request.get("headers")
        path_params = request.get("path_params")
        expected_code = expected.get("status_code", 200)
        checks = expected.get("checks", [])
        tc_id = tc.get("id", "")

        # 选择 client 变量
        use_auth = "已登录" in tc.get("precondition", "")
        client_var = "auth_client" if use_auth else "client"

        lines = [
            f'def test_{method_name}(self, {client_var}):',
            f'    """{tc_id}: {tc.get("test_point", "")}"""',
        ]

        priority = tc.get("priority", "")
        if priority:
            lines.insert(0, f'@pytest.mark.{priority}')

        if path_params:
            lines.append(f'    path = "{path}".format(**{json.dumps(path_params, ensure_ascii=False)})')
        else:
            lines.append(f'    path = "{path}"')

        # 构建请求参数
        kwargs = []
        if body is not None:
            kwargs.append(f'json={json.dumps(body, ensure_ascii=False)}')
        if query_params:
            kwargs.append(f'params={json.dumps(query_params, ensure_ascii=False)}')
        if headers:
            kwargs.append(f'headers={json.dumps(headers, ensure_ascii=False)}')

        kwargs_str = ', ' + ', '.join(kwargs) if kwargs else ''
        lines.append(f'    resp = {client_var}.{http_method}(path{kwargs_str})')

        # 断言
        lines.append(f'    assert resp.status_code == {expected_code}')

        # 额外检查
        for check in checks:
            if "包含" in check:
                match = re.search(r"'(.+?)'", check)
                if match:
                    keyword = match.group(1)
                    lines.append(f'    assert "{keyword}" in resp.text')
            elif "非空" in check or "not None" in check.lower():
                lines.append(f'    assert resp.json() is not None')

        return '\n'.join(lines)

    def _tc_to_unique_method_name(self, tc: dict, existing_names: set) -> str:
        """将用例转为唯一的方法名"""
        # 优先用 test_point 生成
        point = tc.get("test_point", "")
        name = self._point_to_method_name(point)

        # 如果冲突，加上 tc_id 后缀
        tc_id = tc.get("id", "")
        if name in existing_names:
            # 加上 ID 数字后缀
            id_suffix = re.sub(r'[^0-9]', '', tc_id)
            name = f"{name}_{id_suffix}" if id_suffix else f"{name}_{len(existing_names)}"

        return name or f"test_{tc_id.replace('-', '_').lower()}"

    def _point_to_method_name(self, point: str) -> str:
        """将 test_point 转为方法名"""
        # 清理中文和特殊字符
        name = re.sub(r'[^a-zA-Z0-9_]', '_', point)
        name = re.sub(r'_+', '_', name).strip('_').lower()
        if len(name) > 50:
            name = name[:50]
        return name or "test_case"

    def _gen_conftest(self, testcases: list[dict]) -> str:
        """生成 conftest.py"""
        return '''# -*- coding: utf-8 -*-
"""pytest conftest - 全局 fixture 定义"""

import os
import pytest
import yaml
from pathlib import Path
from api_client import ApiClient


def load_config():
    """加载配置文件"""
    config_path = Path(__file__).parent / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}


@pytest.fixture(scope="session")
def config():
    """项目配置"""
    return load_config()


@pytest.fixture(scope="session")
def base_url(config):
    """API 基础 URL"""
    url = config.get("env", {}).get("base_url", "")
    if not url:
        pytest.skip("未配置 base_url，请在 config.yaml 中填写")
    return url.rstrip("/")


@pytest.fixture(scope="session")
def auth_info(config):
    """认证信息"""
    auth = config.get("auth", {})
    auth_type = auth.get("type", "bearer")

    if auth_type == "bearer":
        token = auth.get("token", "")
        if not token:
            login_config = auth.get("login", {})
            if login_config.get("url"):
                # TODO: 自动登录获取 token
                pass
            if not token:
                pytest.skip("未配置 token，请在 config.yaml 中填写")
        return {"type": "bearer", "token": token}

    return {"type": auth_type}


@pytest.fixture(scope="session")
def client(base_url):
    """API 客户端（无认证）"""
    return ApiClient(base_url)


@pytest.fixture(scope="session")
def auth_client(base_url, auth_info):
    """API 客户端（带认证）"""
    return ApiClient(base_url, auth=auth_info)


# XTestRunner 报告集成（可选）
try:
    from XTestRunner import HTMLTestRunner

    def pytest_configure(config):
        """配置 XTestRunner"""
        # 注册自定义标记
        config.addinivalue_line("markers", "smoke: 冒烟测试")
        config.addinivalue_line("markers", "regression: 回归测试")
        config.addinivalue_line("markers", "P0: 一级优先级用例")
        config.addinivalue_line("markers", "P1: 二级优先级用例")
        config.addinivalue_line("markers", "P2: 三级优先级用例")
        config.addinivalue_line("markers", "P3: 四级优先级用例")

    def pytest_terminal_summary(terminalreporter, exitstatus, config):
        """在测试结束后生成 XTestRunner 报告"""
        # 获取测试结果
        stats = terminalreporter.stats

        # 计算统计
        passed = len(stats.get('passed', []))
        failed = len(stats.get('failed', []))
        error = len(stats.get('error', []))
        skipped = len(stats.get('skipped', []))
        total = passed + failed + error + skipped

        if total == 0:
            return

        # 生成报告路径
        report_dir = os.environ.get('REPORT_DIR', './report')
        os.makedirs(report_dir, exist_ok=True)
        report_path = os.path.join(report_dir, 'xtestrunner_report.html')

        try:
            # 创建 XTestRunner 实例
            runner = HTMLTestRunner(
                title=os.environ.get('REPORT_TITLE', 'API 测试报告'),
                tester=os.environ.get('REPORT_TESTER', ''),
                description=os.environ.get('REPORT_DESCRIPTION', ''),
                language='cn'
            )

            # 这里需要将 pytest 结果转换为 unittest 格式
            # 由于 XTestRunner 不直接支持 pytest，我们使用简化版本
            print(f"\\n[XTestRunner] 测试完成: {total} 个用例")
            print(f"[XTestRunner] 通过: {passed}, 失败: {failed}, 错误: {error}, 跳过: {skipped}")
            print(f"[XTestRunner] 报告生成需要使用 run_tests.py 脚本")

        except Exception as e:
            print(f"[WARN] XTestRunner 报告生成失败: {e}")

except ImportError:
    # XTestRunner 未安装，跳过
    pass
'''

    def _gen_api_client(self) -> str:
        """生成 api_client.py"""
        return '''# -*- coding: utf-8 -*-
"""API 请求客户端封装"""

import json
import time
import logging
import requests

logger = logging.getLogger(__name__)


class ApiClient:
    """API 请求客户端"""

    def __init__(self, base_url: str, auth: dict = None, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.auth = auth or {}
        self.timeout = timeout
        self.session = requests.Session()
        self._setup_auth()

    def _setup_auth(self):
        """设置认证信息"""
        auth_type = self.auth.get("type", "")
        if auth_type == "bearer":
            token = self.auth.get("token", "")
            self.session.headers["Authorization"] = f"Bearer {token}"
        elif auth_type == "basic":
            username = self.auth.get("username", "")
            password = self.auth.get("password", "")
            self.session.auth = (username, password)
        elif auth_type == "api_key":
            key = self.auth.get("key", "")
            header_name = self.auth.get("header_name", "X-API-Key")
            self.session.headers[header_name] = key

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        """发送请求"""
        url = f"{self.base_url}{path}"
        kwargs.setdefault("timeout", self.timeout)

        start = time.time()
        logger.info(f">>> {method} {url}")
        if "json" in kwargs:
            logger.info(f"    Body: {json.dumps(kwargs['json'], ensure_ascii=False)}")

        resp = self.session.request(method, url, **kwargs)

        elapsed = (time.time() - start) * 1000
        logger.info(f"<<< {resp.status_code} ({elapsed:.0f}ms)")
        logger.info(f"    Response: {resp.text[:500]}")

        return resp

    def get(self, path: str, **kwargs) -> requests.Response:
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        return self._request("POST", path, **kwargs)

    def put(self, path: str, **kwargs) -> requests.Response:
        return self._request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        return self._request("DELETE", path, **kwargs)

    def patch(self, path: str, **kwargs) -> requests.Response:
        return self._request("PATCH", path, **kwargs)
'''

    def _gen_config(self, project_name: str, base_url: str) -> str:
        """生成 config.yaml"""
        return f'''# API 测试配置文件
# 使用前请填写实际的环境信息

project:
  name: "{project_name}"

env:
  base_url: "{base_url}"  # 请填写实际 API 地址
  timeout: 30
  verify_ssl: true

auth:
  type: bearer
  token: ""  # 请填写实际 token
  # 或配置自动获取:
  # login:
  #   url: /api/login
  #   method: POST
  #   body:
  #     username: ""
  #     password: ""
  #   token_path: data.token

run:
  priority: [P0, P1]
  parallel: false
  retry: 1

report:
  format: [xtestrunner, markdown]
  output: ./report
  title: "{project_name} - API 测试报告"
  description: ""
  tester: ""
  template: 1
  language: cn
'''

    def _gen_requirements(self) -> str:
        """生成 requirements.txt"""
        return '''pytest>=7.0.0
requests>=2.28.0
PyYAML>=6.0
XTestRunner>=1.0.0
'''
