#!/usr/bin/env python3
# build.py - 从统一源生成三种平台格式的 skill 文件
# 用法: python3 build.py [--clean]

import os
import sys
import yaml
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SKILLS_DIR = SCRIPT_DIR / "skills"
DIST_DIR = SCRIPT_DIR / "dist"


def load_yaml(file_path):
    """加载 YAML 文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def replace_variables(value, variables):
    """替换模板变量 {{variable}}"""
    if not isinstance(value, str):
        return value
    for key, val in variables.items():
        value = value.replace(f'{{{{{key}}}}}', str(val))
    return value


def generate_platform_file(skill_dir, platform, meta, prompt_content):
    """为指定平台生成 skill 文件"""
    skill_name = skill_dir.name

    # 获取平台配置
    platforms = meta.get('platforms', {})
    platform_config = platforms.get(platform)
    if not platform_config:
        print(f"[SKIP] {skill_name}: 未找到 {platform} 配置")
        return

    # 获取输出路径
    output_path = platform_config.get('path')
    if not output_path:
        print(f"[SKIP] {skill_name}: {platform} 缺少 path 配置")
        return

    # 准备变量
    variables = {
        'name': meta.get('name', ''),
        'description': meta.get('description', ''),
        'version': meta.get('version', ''),
    }

    # 获取 frontmatter 配置
    frontmatter_config = platform_config.get('frontmatter', {})
    frontmatter = {}
    for key, value in frontmatter_config.items():
        frontmatter[key] = replace_variables(value, variables)

    # 获取 prepend 内容
    prepend = platform_config.get('prepend', '')

    # 构建输出文件路径
    output_file = DIST_DIR / output_path
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        # 写入 YAML frontmatter
        f.write('---\n')
        for key, value in frontmatter.items():
            if isinstance(value, list):
                f.write(f'{key}:\n')
                for item in value:
                    f.write(f'  - {item}\n')
            else:
                # 如果值包含特殊字符，用引号包围
                if any(c in str(value) for c in ':{}[],&*#?|<>=!%@`'):
                    f.write(f'{key}: "{value}"\n')
                else:
                    f.write(f'{key}: {value}\n')
        f.write('---\n\n')

        # 写入 prepend 内容（如果有）
        if prepend:
            f.write(prepend)
            f.write('\n')

        # 写入 prompt.md 内容
        f.write(prompt_content)

    print(f"[OK] 生成: {output_file}")


def main():
    # 处理命令行参数
    clean = '--clean' in sys.argv

    # 清理 dist 目录
    if clean:
        print("[CLEAN] 清理 dist 目录...")
        import shutil
        if DIST_DIR.exists():
            shutil.rmtree(DIST_DIR)

    # 创建 dist 目录结构
    (DIST_DIR / ".claude" / "commands").mkdir(parents=True, exist_ok=True)
    (DIST_DIR / ".cursor" / "skills").mkdir(parents=True, exist_ok=True)
    (DIST_DIR / ".agents" / "skills").mkdir(parents=True, exist_ok=True)

    # 处理每个 skill
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue

        skill_name = skill_dir.name
        print(f"\n{'='*40}")
        print(f"处理 Skill: {skill_name}")
        print(f"{'='*40}")

        # 加载 meta.yaml
        meta_file = skill_dir / "meta.yaml"
        if not meta_file.exists():
            print(f"[SKIP] {skill_name}: 缺少 meta.yaml")
            continue

        meta = load_yaml(meta_file)

        # 加载 prompt.md
        prompt_file = skill_dir / "prompt.md"
        if not prompt_file.exists():
            print(f"[SKIP] {skill_name}: 缺少 prompt.md")
            continue

        with open(prompt_file, 'r', encoding='utf-8') as f:
            prompt_content = f.read()

        # 为每个平台生成文件
        for platform in ['claude', 'cursor', 'agents']:
            generate_platform_file(skill_dir, platform, meta, prompt_content)

    print(f"\n{'='*40}")
    print("构建完成！")
    print(f"{'='*40}")
    print(f"\n生成的文件在 dist/ 目录下：")
    for md_file in sorted(DIST_DIR.rglob("*.md")):
        print(f"  {md_file.relative_to(SCRIPT_DIR)}")
    print(f"\n要部署到项目根目录，请运行:")
    print(f"  cp -r dist/.claude .claude")
    print(f"  cp -r dist/.cursor .cursor")
    print(f"  cp -r dist/.agents .agents")


if __name__ == '__main__':
    main()
