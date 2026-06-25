#!/bin/bash
# build.sh - 从统一源生成三种平台格式的 skill 文件
# 用法: ./build.sh [--clean]
# 依赖: Python 3, PyYAML

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -n "$PYTHON" ]; then
    PYTHON_BIN="$PYTHON"
elif [ -x "$SCRIPT_DIR/.venv/bin/python" ]; then
    PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
else
    PYTHON_BIN="$(command -v python3 || true)"
fi

if [ -z "$PYTHON_BIN" ] || [ ! -x "$PYTHON_BIN" ]; then
    echo "[ERROR] 未找到 Python，请先运行 ./setup.sh"
    exit 1
fi

if ! "$PYTHON_BIN" -c "import yaml" >/dev/null 2>&1; then
    echo "[ERROR] 未找到 PyYAML，请先运行 ./setup.sh 或安装 requirements.txt"
    exit 1
fi

# 调用 Python 构建脚本
"$PYTHON_BIN" "$SCRIPT_DIR/build.py" "$@"
