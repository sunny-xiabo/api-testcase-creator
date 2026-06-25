#!/bin/bash
# init-api-testcase.sh - 将 api-testcase-creator 框架部署到目标项目
# 用法: ./init-api-testcase.sh <project-name> <target-path> [--force]
# 示例: ./init-api-testcase.sh _template /path/to/my-project

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="${1:-}"
TARGET_PATH="${2:-}"
FORCE=false

# 解析参数
for arg in "$@"; do
    case "$arg" in
        --force) FORCE=true ;;
    esac
done

# 参数校验
if [ -z "$PROJECT_NAME" ]; then
    echo "[ERROR] 请提供项目名称"
    echo "用法: $0 <project-name> <target-path> [--force]"
    echo ""
    echo "可用项目:"
    for dir in "$SCRIPT_DIR/projects"/*/; do
        if [ -d "$dir" ]; then
            name=$(basename "$dir")
            echo "  - $name"
        fi
    done
    exit 1
fi

if [ -z "$TARGET_PATH" ]; then
    echo "[ERROR] 请提供目标路径"
    echo "用法: $0 <project-name> <target-path> [--force]"
    exit 1
fi

# 检查项目是否存在
PROJECT_DIR="$SCRIPT_DIR/projects/$PROJECT_NAME"
if [ ! -d "$PROJECT_DIR" ]; then
    echo "[ERROR] 项目 '$PROJECT_NAME' 不存在"
    echo "可用项目:"
    for dir in "$SCRIPT_DIR/projects"/*/; do
        if [ -d "$dir" ]; then
            echo "  - $(basename "$dir")"
        fi
    done
    exit 1
fi

# 确保 dist 目录存在
DIST_DIR="$SCRIPT_DIR/dist"
if [ ! -d "$DIST_DIR" ]; then
    echo "[INFO] dist 目录不存在，正在构建..."
    bash "$SCRIPT_DIR/build.sh"
fi

# 创建目标目录
TARGET_PATH="$(cd "$TARGET_PATH" 2>/dev/null && pwd || echo "$TARGET_PATH")"
mkdir -p "$TARGET_PATH"

echo "=========================================="
echo "部署 api-testcase-creator"
echo "=========================================="
echo "项目: $PROJECT_NAME"
echo "目标: $TARGET_PATH"
echo "=========================================="

# 复制函数（支持 --force 覆盖）
copy_item() {
    local src="$1"
    local dst="$2"
    if [ -e "$dst" ] && [ "$FORCE" = false ]; then
        echo "[SKIP] $dst 已存在（使用 --force 覆盖）"
        return
    fi
    mkdir -p "$(dirname "$dst")"
    cp -r "$src" "$dst"
    echo "[OK] $dst"
}

# 1. 部署 skill 文件
echo ""
echo ">> 部署 Skill 文件"
if [ -d "$DIST_DIR/.claude" ]; then
    copy_item "$DIST_DIR/.claude" "$TARGET_PATH/.claude"
fi
if [ -d "$DIST_DIR/.cursor" ]; then
    copy_item "$DIST_DIR/.cursor" "$TARGET_PATH/.cursor"
fi
if [ -d "$DIST_DIR/.agents" ]; then
    copy_item "$DIST_DIR/.agents" "$TARGET_PATH/.agents"
fi

# 2. 部署框架文件
echo ""
echo ">> 部署框架文件"
ASSETS_DIR="$TARGET_PATH/.api-testcase-assets"
mkdir -p "$ASSETS_DIR/templates" "$ASSETS_DIR/scripts" "$ASSETS_DIR/history" "$ASSETS_DIR/framework"

# 复制模板
if [ -d "$SCRIPT_DIR/framework/templates" ]; then
    cp -r "$SCRIPT_DIR/framework/templates/"* "$ASSETS_DIR/templates/"
    echo "[OK] 模板文件 -> $ASSETS_DIR/templates/"
fi

# 复制脚本
if [ -d "$SCRIPT_DIR/framework/scripts" ]; then
    cp -r "$SCRIPT_DIR/framework/scripts/"* "$ASSETS_DIR/scripts/"
    chmod +x "$ASSETS_DIR/scripts/"*.py
    echo "[OK] 脚本文件 -> $ASSETS_DIR/scripts/"
fi

# 复制运行脚本依赖的框架包
if [ -f "$SCRIPT_DIR/framework/__init__.py" ]; then
    cp "$SCRIPT_DIR/framework/__init__.py" "$ASSETS_DIR/framework/"
fi
for pkg in parsers generators runners; do
    if [ -d "$SCRIPT_DIR/framework/$pkg" ]; then
        rm -rf "$ASSETS_DIR/framework/$pkg"
        mkdir -p "$ASSETS_DIR/framework/$pkg"
        find "$SCRIPT_DIR/framework/$pkg" -type f -name "*.py" -exec cp {} "$ASSETS_DIR/framework/$pkg/" \;
        echo "[OK] $pkg 包 -> $ASSETS_DIR/framework/$pkg/"
    fi
done

# 复制框架配置
for f in review-dimensions.yaml scene-types.yaml; do
    if [ -f "$SCRIPT_DIR/framework/$f" ]; then
        cp "$SCRIPT_DIR/framework/$f" "$ASSETS_DIR/"
        echo "[OK] $f -> $ASSETS_DIR/"
    fi
done

# 3. 部署项目资产
echo ""
echo ">> 部署项目资产"
for f in project.config.md api-checkpoints.md api-review-dimensions.md; do
    if [ -f "$PROJECT_DIR/$f" ]; then
        copy_item "$PROJECT_DIR/$f" "$ASSETS_DIR/$f"
    fi
done

# 4. 初始化历史索引
HISTORY_INDEX="$ASSETS_DIR/history/history-index.md"
if [ ! -f "$HISTORY_INDEX" ]; then
    cat > "$HISTORY_INDEX" << 'EOF'
# 运行历史索引

| 序号 | 运行时间 | 模块名 | 用例数 | 通过率 | 报告路径 |
|------|----------|--------|--------|--------|----------|
EOF
    echo "[OK] $HISTORY_INDEX"
fi

# 5. 更新 .gitignore
GITIGNORE="$TARGET_PATH/.gitignore"
if [ -f "$GITIGNORE" ]; then
    if ! grep -q ".api-testcase-assets/history/" "$GITIGNORE" 2>/dev/null; then
        echo "" >> "$GITIGNORE"
        echo "# API 测试用例生成历史记录" >> "$GITIGNORE"
        echo ".api-testcase-assets/history/" >> "$GITIGNORE"
        echo "[OK] 已更新 .gitignore"
    fi
else
    cat > "$GITIGNORE" << 'EOF'
# API 测试用例生成历史记录
.api-testcase-assets/history/
EOF
    echo "[OK] 已创建 .gitignore"
fi

# 6. 生成 Claude Code 权限配置
SETTINGS_FILE="$TARGET_PATH/.claude/settings.local.json"
if [ ! -f "$SETTINGS_FILE" ]; then
    mkdir -p "$TARGET_PATH/.claude"
    cat > "$SETTINGS_FILE" << EOF
{
  "permissions": {
    "allow": [
      "Bash(python3 .api-testcase-assets/scripts/*.py *)",
      "Bash(python3 -m pytest *)",
      "Bash(pip3 install *)",
      "Bash(pip install *)"
    ]
  }
}
EOF
    echo "[OK] $SETTINGS_FILE"
fi

# 输出完成信息
echo ""
echo "=========================================="
echo "部署完成！"
echo "=========================================="
echo ""
echo "目录结构:"
echo "  $TARGET_PATH/"
echo "  ├── .claude/commands/"
echo "  │   ├── api-testcase-creator.md   # 生成测试用例和代码"
echo "  │   └── api-testcase-runner.md    # 运行测试和生成报告"
echo "  ├── .api-testcase-assets/"
echo "  │   ├── project.config.md"
echo "  │   ├── api-checkpoints.md"
echo "  │   ├── api-review-dimensions.md"
echo "  │   ├── review-dimensions.yaml"
echo "  │   ├── scene-types.yaml"
echo "  │   ├── templates/"
echo "  │   ├── scripts/"
echo "  │   └── history/"
echo "  └── .gitignore"
echo ""
echo "可用命令:"
echo "  /api-testcase-creator  - 从接口文档生成测试用例和代码"
echo "  /api-testcase-runner   - 运行测试用例并生成报告"
echo ""
echo "下一步:"
echo "  1. 编辑 $ASSETS_DIR/project.config.md 填写项目信息"
echo "  2. 编辑 $ASSETS_DIR/api-checkpoints.md 补充项目特定检查点"
echo "  3. 在 Claude Code 中触发 /api-testcase-creator 开始生成"
