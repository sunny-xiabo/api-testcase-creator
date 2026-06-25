#!/bin/bash
# setup.sh - 一键初始化 api-testcase-creator
# 用法:
#   ./setup.sh [target-path] [--force]
#   ./setup.sh --system [target-path] [--force]
#   ./setup.sh --python /path/to/python [target-path] [--force]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

USE_SYSTEM=false
CUSTOM_PYTHON=""
TARGET_PATH=""
FORCE=false

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
        --force)
            FORCE=true
            shift
            ;;
        -h|--help)
            sed -n '1,8p' "$0"
            exit 0
            ;;
        *)
            if [ -z "$TARGET_PATH" ]; then
                TARGET_PATH="$1"
                shift
            else
                echo "[ERROR] 未识别参数: $1"
                exit 1
            fi
            ;;
    esac
done

resolve_python() {
    if [ -n "$CUSTOM_PYTHON" ]; then
        echo "$CUSTOM_PYTHON"
        return
    fi

    if [ "$USE_SYSTEM" = true ]; then
        if command -v python3 >/dev/null 2>&1; then
            command -v python3
            return
        fi
        echo "[ERROR] 未找到 python3" >&2
        exit 1
    fi

    if [ ! -x ".venv/bin/python" ]; then
        if ! command -v python3 >/dev/null 2>&1; then
            echo "[ERROR] 未找到 python3，无法创建 .venv"
            exit 1
        fi
        echo "[1/4] 创建虚拟环境 .venv" >&2
        python3 -m venv .venv
    else
        echo "[1/4] 复用虚拟环境 .venv" >&2
    fi
    echo "$SCRIPT_DIR/.venv/bin/python"
}

PYTHON_BIN="$(resolve_python)"

echo "[INFO] Python: $PYTHON_BIN"
"$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit("[ERROR] 需要 Python >= 3.10")
print(f"[INFO] Python 版本: {sys.version.split()[0]}")
PY

echo "[2/4] 安装依赖"
if ! "$PYTHON_BIN" -m pip --version >/dev/null 2>&1; then
    echo "[WARN] 当前 Python 没有 pip，尝试启用 ensurepip"
    if ! "$PYTHON_BIN" -m ensurepip --upgrade >/dev/null 2>&1; then
        echo "[ERROR] 当前 Python 没有 pip，请先安装 pip，或使用默认 .venv 模式"
        exit 1
    fi
fi

if ! "$PYTHON_BIN" -m pip install -r requirements.txt; then
    cat <<'EOF'
[ERROR] 依赖安装失败。
如果你使用的是 Homebrew 管理的系统 Python，可能受到 PEP 668 限制。
建议改用默认模式：
  ./setup.sh
或使用 Conda/自定义 Python：
  ./setup.sh --python /path/to/python
EOF
    exit 1
fi

echo "[3/4] 构建 Skill"
PYTHON="$PYTHON_BIN" "$SCRIPT_DIR/build.sh" --clean

if [ -n "$TARGET_PATH" ]; then
    echo "[4/4] 部署到目标项目"
    if [ "$FORCE" = true ]; then
        "$SCRIPT_DIR/init-api-testcase.sh" _template "$TARGET_PATH" --force
    else
        "$SCRIPT_DIR/init-api-testcase.sh" _template "$TARGET_PATH"
    fi
else
    echo "[4/4] 跳过部署"
fi

cat <<EOF

[OK] 初始化完成
可用命令:
  ./doctor.sh
  PYTHON="$PYTHON_BIN" ./build.sh --clean
  "$PYTHON_BIN" framework/scripts/repair_json.py <input> <output> --schema framework/templates/testcases.schema.json
EOF
