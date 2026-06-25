#!/bin/bash
# doctor.sh - 检查 api-testcase-creator 开发/运行环境
# 用法:
#   ./doctor.sh
#   ./doctor.sh --system
#   ./doctor.sh --python /path/to/python

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

USE_SYSTEM=false
CUSTOM_PYTHON=""

while [ $# -gt 0 ]; do
    case "$1" in
        --system)
            USE_SYSTEM=true
            shift
            ;;
        --python)
            CUSTOM_PYTHON="${2:-}"
            if [ -z "$CUSTOM_PYTHON" ]; then
                echo "[ERROR] --python 需要指定 Python 路径"
                exit 1
            fi
            shift 2
            ;;
        -h|--help)
            sed -n '1,6p' "$0"
            exit 0
            ;;
        *)
            echo "[ERROR] 未识别参数: $1"
            exit 1
            ;;
    esac
done

if [ -n "$CUSTOM_PYTHON" ]; then
    PYTHON_BIN="$CUSTOM_PYTHON"
elif [ "$USE_SYSTEM" = true ]; then
    PYTHON_BIN="$(command -v python3 || true)"
elif [ -x ".venv/bin/python" ]; then
    PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
else
    PYTHON_BIN="$(command -v python3 || true)"
fi

if [ -z "$PYTHON_BIN" ] || [ ! -x "$PYTHON_BIN" ]; then
    echo "[FAIL] Python 不可用"
    exit 1
fi

echo "[INFO] Python: $PYTHON_BIN"
"$PYTHON_BIN" - <<'PY'
import importlib.util
import sys

print(f"[INFO] Python 版本: {sys.version.split()[0]}")
if sys.version_info < (3, 10):
    raise SystemExit("[FAIL] Python 版本需 >= 3.10")

checks = [
    ("yaml", "PyYAML"),
    ("json_repair", "json-repair"),
]
failed = []
for module, package in checks:
    if importlib.util.find_spec(module):
        print(f"[OK] {package} 已安装")
    else:
        print(f"[FAIL] {package} 未安装")
        failed.append(package)

if failed:
    raise SystemExit("[FAIL] 依赖缺失，请运行 ./setup.sh 或 ./setup.sh --system")
PY

"$PYTHON_BIN" build.py --clean >/tmp/api-testcase-doctor-build.log
echo "[OK] build.py 可运行"

TMP_DIR="$(mktemp -d)"
cat > "$TMP_DIR/raw.md" <<'EOF'
```json
[{"id":"TC-001","endpoint":"GET /api/users","test_point":"正向查询","request":{"method":"GET","path":"/api/users"},"precondition":"无","expected":{"status_code":200},"checkpoint":"API-BASIC","scene_type":"正向","priority":"P0"}]
```
EOF

"$PYTHON_BIN" framework/scripts/repair_json.py \
    "$TMP_DIR/raw.md" \
    "$TMP_DIR/out.json" \
    --schema framework/templates/testcases.schema.json >/tmp/api-testcase-doctor-repair.log
echo "[OK] repair_json.py 可运行"

echo "[OK] 环境检查通过"
