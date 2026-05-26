#!/usr/bin/env python3
"""
自动流水线调度 - 平衡模式版本
一键跑完所有流程，自动适配模式，断点续跑
"""
import os
import sys
import subprocess
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "out_doc"
MD_FILES_DIR = OUTPUT_DIR / "md_file"
CHAPTERS_DIR = OUTPUT_DIR / "chapters"

# 模式配置，统一读取
NOVEL_MODE = os.environ.get("AUTONOVEL_MODE", "balance").lower()
# 模式说明
MODE_DESC = {
    "balance": "平衡模式（有质感的网文，默认）",
    "shuangwen": "爽文模式（标准化番茄爽文）",
    "literature": "文学模式（西方文学风格）"
}

# 所有流水线步骤，按顺序
STEPS = [
    ("gen_world", "生成世界设定", "python gen_world.py"),
    ("gen_characters", "生成角色设定", "python gen_characters.py"),
    ("gen_outline", "生成章节大纲", "python gen_outline.py"),
    ("draft_chapters", "生成章节草稿", "python draft_chapter.py {}"),
    ("revise_chapters", "润色章节", "python revise_chapter.py {}"),
    ("evaluate_chapters", "评估章节", "python evaluate.py --chapter {}"),
    ("export", "导出完整小说", "python export.py")
]

def run_command(cmd):
    """运行命令，实时输出"""
    print(f"\n>>> 执行: {cmd}")
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=BASE_DIR,
            check=True,
            stdout=sys.stdout,
            stderr=sys.stderr,
            env=os.environ.copy() # 继承环境变量，确保子脚本能读到AUTONOVEL_MODE
        )
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"命令执行失败: {e}")
        return False

def check_step_done(step_name, chapter_num=None):
    """检查步骤是否已经完成，支持断点续跑"""
    if step_name == "gen_world":
        return (MD_FILES_DIR / "世界设定.md").exists()
    elif step_name == "gen_characters":
        return (MD_FILES_DIR / "角色设定.md").exists()
    elif step_name == "gen_outline":
        return (MD_FILES_DIR / "章节大纲.md").exists()
    elif step_name == "draft_chapters":
        # 检查章节草稿是否存在
        files = list(CHAPTERS_DIR.glob(f"第{chapter_num}章_*.md"))
        if not files:
            files = list(CHAPTERS_DIR.glob(f"ch_{chapter_num:02d}.md"))
        return len(files) > 0
    elif step_name == "revise_chapters":
        # 检查润色后的章节
        files = list(CHAPTERS_DIR.glob(f"第{chapter_num}章_*.md"))
        if files:
            # 简单检查文件大小，润色后的会更大一点
            return files[0].stat().st_size > 1000
        return False
    elif step_name == "evaluate_chapters":
        # 检查评估日志
        logs = list(Path(BASE_DIR / "eval_logs").glob(f"*_ch{chapter_num:02d}_{NOVEL_MODE}.json"))
        return len(logs) > 0
    elif step_name == "export":
        return (OUTPUT_DIR / "完整小说.md").exists()
    return False

def get_chapter_count():
    """从大纲里读取有多少章"""
    outline_path = MD_FILES_DIR / "章节大纲.md"
    if not outline_path.exists():
        return 0
    outline = outline_path.read_text()
    # 匹配中文章节
    ch_count = len(re.findall(r'###\s*第\d+章', outline))
    if ch_count > 0:
        return ch_count
    # 匹配英文章节
    ch_count = len(re.findall(r'###\s*Ch\s*\d+', outline))
    return ch_count

def main():
    parser = argparse.ArgumentParser(description="自动流水线调度")
    parser.add_argument("--from-step", type=str, default=None, help="从哪个步骤开始")
    parser.add_argument("--to-step", type=str, default=None, help="到哪个步骤结束")
    parser.add_argument("--only-chapter", type=int, default=None, help="只处理指定章节")
    parser.add_argument("--skip-done", action="store_true", default=True, help="跳过已经完成的步骤")
    args = parser.parse_args()

    # 打印模式信息
    print("="*60)
    print(f"AutoNovel 自动流水线 - 模式: {MODE_DESC.get(NOVEL_MODE, NOVEL_MODE)}")
    print(f"工作目录: {BASE_DIR}")
    print("="*60)

    # 确保目录存在
    OUTPUT_DIR.mkdir(exist_ok=True)
    MD_FILES_DIR.mkdir(exist_ok=True)
    CHAPTERS_DIR.mkdir(exist_ok=True)
    Path(BASE_DIR / "eval_logs").mkdir(exist_ok=True)

    # 检查API配置
    api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("错误：请先在 .env 中设置 API_KEY，然后运行 source .env")
        sys.exit(1)

    # 解析步骤范围
    step_names = [s[0] for s in STEPS]
    start_idx = 0
    if args.from_step:
        if args.from_step not in step_names:
            print(f"错误：未知的步骤 {args.from_step}，可用步骤: {step_names}")
            sys.exit(1)
        start_idx = step_names.index(args.from_step)
    
    end_idx = len(STEPS)
    if args.to_step:
        if args.to_step not in step_names:
            print(f"错误：未知的步骤 {args.to_step}，可用步骤: {step_names}")
            sys.exit(1)
        end_idx = step_names.index(args.to_step) + 1

    # 运行步骤
    for i in range(start_idx, end_idx):
        step_name, step_desc, step_cmd = STEPS[i]
        print(f"\n--- 步骤 {i+1}/{len(STEPS)}: {step_desc} ---")

        # 基础步骤（非章节相关）
        if step_name not in ["draft_chapters", "revise_chapters", "evaluate_chapters"]:
            if args.skip_done and check_step_done(step_name):
                print(f"✓ 步骤已完成，跳过")
                continue
            
            if not run_command(step_cmd):
                print(f"步骤 {step_desc} 失败，终止流水线")
                sys.exit(1)
            continue
        
        # 章节相关的步骤，批量处理
        chapter_count = get_chapter_count()
        if chapter_count == 0:
            print("错误：无法获取章节数量，请先运行大纲生成")
            sys.exit(1)
        
        # 处理章节范围
        if args.only_chapter:
            chapters = [args.only_chapter]
        else:
            chapters = list(range(1, chapter_count + 1))
        
        print(f"需要处理 {len(chapters)} 个章节")
        for ch_num in chapters:
            print(f"\n  处理第 {ch_num} 章...")
            if args.skip_done and check_step_done(step_name, ch_num):
                print(f"  ✓ 第{ch_num}章已完成，跳过")
                continue
            
            cmd = step_cmd.format(ch_num)
            if not run_command(cmd):
                print(f"  第{ch_num}章处理失败，终止流水线")
                sys.exit(1)

    print("\n" + "="*60)
    print(f"🎉 流水线全部完成！模式：{MODE_DESC.get(NOVEL_MODE, NOVEL_MODE)}")
    print(f"输出文件都在: {OUTPUT_DIR}")
    print("="*60)

if __name__ == "__main__":
    # 导入re，因为上面用了re
    import re
    main()