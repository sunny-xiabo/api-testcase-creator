import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from framework.generators.base_case_gen import BaseCaseGenerator
from framework.generators.code_gen import CodeGenerator
from framework.generators.postman_gen import PostmanGenerator
from framework.parsers.endpoint_model import Endpoint, Param
from framework.parsers.openapi_parser import OpenAPIParser
from framework.runners.pytest_runner import PytestRunner, XTestRunnerReporter
from framework.runners.runner_shared import summarize_pytest_output
from framework.scripts.repair_json import extract_json_text, normalize_json


def test_build_request_includes_path_params():
    ep = Endpoint(
        method="GET",
        path="/api/users/{id}",
        parameters=[
            Param(name="id", location="path", type="integer", required=True),
            Param(name="page", location="query", type="integer", required=False),
        ],
    )

    request = BaseCaseGenerator()._build_request(ep)

    assert request["path_params"]["id"] == 1
    assert request["path"] == "/api/users/{id}"


def test_gen_test_method_formats_path_and_marks_priority():
    tc = {
        "id": "TC-001",
        "test_point": "正向调用",
        "priority": "P0",
        "request": {
            "method": "GET",
            "path": "/api/users/{id}",
            "path_params": {"id": 1},
        },
        "expected": {"status_code": 200, "checks": []},
    }

    code = CodeGenerator()._gen_test_method(tc, set())

    assert "@pytest.mark.P0" in code
    assert 'path = "/api/users/{id}".format(**{"id": 1})' in code
    assert "resp = client.get(path)" in code


def test_pick_content_schema_prefers_non_json_content():
    parser = OpenAPIParser()
    schema, example = parser._pick_content_schema(
        {
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                },
                "example": {"name": "demo"},
            }
        }
    )

    assert schema["type"] == "object"
    assert example == {"name": "demo"}


def test_schema_to_fields_flattens_nested_object():
    parser = OpenAPIParser()
    fields = parser._schema_to_fields(
        {
            "type": "object",
            "required": ["user"],
            "properties": {
                "user": {
                    "type": "object",
                    "required": ["name"],
                    "properties": {
                        "name": {"type": "string"},
                    },
                }
            },
        }
    )

    assert [field.name for field in fields] == ["user.name"]
    assert fields[0].required is True


def test_positive_case_adds_response_key_checks():
    ep = Endpoint(
        method="GET",
        path="/api/users",
        responses=[
            type(
                "Resp",
                (),
                {
                    "status_code": 200,
                    "schema": {"properties": {"id": {}, "name": {}}},
                    "example": {"id": 1, "name": "demo"},
                },
            )()
        ],
    )

    case = BaseCaseGenerator()._positive_cases(ep)[0]

    assert "响应体非空" in case["expected"]["checks"]
    assert "响应包含 'id'" in case["expected"]["checks"]


def test_array_object_schema_to_fields_and_body_shape():
    parser = OpenAPIParser()
    fields = parser._schema_to_fields(
        {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                    },
                }
            },
        }
    )

    assert [field.name for field in fields] == ["items[0].name"]

    body = {}
    BaseCaseGenerator()._set_nested_value(body, "items[0].name", "demo")

    assert body == {"items": [{"name": "demo"}]}


def test_combined_schema_to_fields_dedupes_fields():
    parser = OpenAPIParser()
    fields = parser._schema_to_fields(
        {
            "allOf": [
                {"type": "object", "properties": {"id": {"type": "integer"}}},
                {"type": "object", "properties": {"id": {"type": "integer"}, "name": {"type": "string"}}},
            ]
        }
    )

    assert [field.name for field in fields] == ["id", "name"]


def test_postman_url_contains_host_path_and_variables():
    tc = {
        "id": "TC-001",
        "test_point": "详情",
        "request": {
            "method": "GET",
            "path": "/api/users/{id}",
            "path_params": {"id": 1},
            "query_params": {"verbose": True},
        },
        "expected": {"status_code": 200, "checks": []},
    }

    item = PostmanGenerator()._tc_to_request(tc, "")
    url = item["request"]["url"]

    assert url["raw"] == "{{base_url}}/api/users/{{id}}"
    assert url["host"] == ["{{base_url}}"]
    assert url["path"] == ["api", "users", "{{id}}"]
    assert url["variable"] == [{"key": "id", "value": "1"}]
    assert url["query"][0]["key"] == "verbose"


def test_shared_pytest_summary_parser():
    summary = summarize_pytest_output("test_a.py::test_ok PASSED\n2 passed, 1 skipped in 0.12s")

    assert summary["total"] == 3
    assert summary["passed"] == 2
    assert summary["skipped"] == 1


def test_pytest_runner_uses_builtin_html_without_pytest_html(monkeypatch, tmp_path):
    commands = []

    def fake_run(cmd, capture_output, text):
        commands.append(cmd)
        return SimpleNamespace(
            returncode=0,
            stdout="test_a.py::test_ok PASSED\n1 passed in 0.01s",
            stderr="",
        )

    monkeypatch.setattr("framework.runners.pytest_runner.subprocess.run", fake_run)

    summary = PytestRunner(str(tmp_path), str(tmp_path / "report")).run()

    command = commands[0]
    assert "--html" not in command
    assert "--self-contained-html" not in command
    assert summary["html_report"].endswith("html_report.html")
    assert (tmp_path / "report" / "html_report.html").exists()


def test_xtestrunner_option_falls_back_to_builtin_report(tmp_path):
    summary = {
        "stdout": "test_a.py::test_ok PASSED\n1 passed in 0.01s",
        "start_time": "2026-01-01T00:00:00",
        "end_time": "2026-01-01T00:00:01",
    }

    output = XTestRunnerReporter(str(tmp_path)).generate(summary, use_xtestrunner=True)

    assert output.endswith("html_report.html")
    assert os.path.exists(output)


def test_repair_json_extracts_fenced_json_and_validates_schema(tmp_path):
    raw = tmp_path / "raw.md"
    output = tmp_path / "testcases.json"
    schema = os.path.join(os.path.dirname(__file__), "..", "framework", "templates", "testcases.schema.json")
    raw.write_text(
        """下面是用例：

```json
[
  {
    "id": "TC-001",
    "endpoint": "GET /api/users",
    "test_point": "正向查询用户",
    "request": {"method": "GET", "path": "/api/users"},
    "precondition": "无",
    "expected": {"status_code": 200, "checks": ["响应体非空"]},
    "checkpoint": "API-BASIC",
    "scene_type": "正向",
    "priority": "P0"
  }
]
```
""",
        encoding="utf-8",
    )

    summary = normalize_json(str(raw), str(output), schema)

    assert summary["items"] == 1
    assert summary["repaired"] is False
    assert '"id": "TC-001"' in output.read_text(encoding="utf-8")


def test_repair_json_schema_validation_reports_bad_testcase(tmp_path):
    raw = tmp_path / "bad.json"
    output = tmp_path / "testcases.json"
    schema = os.path.join(os.path.dirname(__file__), "..", "framework", "templates", "testcases.schema.json")
    raw.write_text(
        """[
  {
    "id": "BAD-001",
    "endpoint": "GET /api/users",
    "test_point": "正向查询用户",
    "request": {"method": "GET", "path": "/api/users"},
    "precondition": "无",
    "expected": {"status_code": 200},
    "checkpoint": "API-BASIC",
    "scene_type": "正向",
    "priority": "P0"
  }
]""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="pattern"):
        normalize_json(str(raw), str(output), schema)


def test_repair_json_extracts_bare_container():
    text = "前置说明\n[{\"id\":\"TC-001\"}]\n后置说明"

    assert extract_json_text(text) == '[{"id":"TC-001"}]'
