#!/usr/bin/env python3
"""
章节草稿生成 - 完全保留原版逻辑 + 新增自定义素材参考
"""
import os
import re
import argparse
from pathlib import Path
from api_client import call_llm, get_main_model, get_api_key

BASE_DIR = Path(__file__).parent
OUT_DIR = BASE_DIR / "out_doc" / "chapters"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ===================== 【仅新增：加载你的自定义素材】 =====================
# 完全不影响原版任何功能
def load_custom_material():
    material_path = BASE_DIR / "resouse" / "custom_material.md"
    guide_path = BASE_DIR / "resouse" / "write_guide.md"
    material = material_path.read_text(encoding="utf-8") if material_path.exists() else ""
    guide = guide_path.read_text(encoding="utf-8") if guide_path.exists() else ""
    return f"""
【自定义参考素材（可选参考）】
{material}

【自定义写作要求】
{guide}
""" if material or guide else ""
# ========================================================================

def load_book_info():
    md_dir = BASE_DIR / "out_doc" / "md_file"
    world = (md_dir / "世界设定.md").read_text(encoding="utf-8") if (md_dir / "世界设定.md").exists() else ""
    chars = (md_dir / "角色设定.md").read_text(encoding="utf-8") if (md_dir / "角色设定.md").exists() else ""
    outline = (md_dir / "章节大纲.md").read_text(encoding="utf-8") if (md_dir / "章节大纲.md").exists() else ""
    seed = (BASE_DIR / "seed.txt").read_text(encoding="utf-8") if (BASE_DIR / "seed.txt").exists() else ""
    voice = (BASE_DIR / "voice.md").read_text(encoding="utf-8") if (BASE_DIR / "voice.md").exists() else ""
    return world, chars, outline, seed, voice

def get_chapter_outline(chapter_num, outline_text):
    pattern = rf'###\s*第{chapter_num}章.*?(?=###\s*第\d|$)'
    match = re.search(pattern, outline_text, re.DOTALL)
    return match.group(0).strip() if match else f"第{chapter_num}章剧情"

def generate_draft(chapter_num):
    world, chars, outline, seed, voice = load_book_info()
    ch_outline = get_chapter_outline(chapter_num, outline)
    # 加载自定义素材
    custom_content = load_custom_material()

    # ===================== 【原版完整提示词 100% 保留】 =====================
    prompt = f"""
你是专业网文作者，根据以下信息创作小说章节正文。

【作品灵感】
{seed}

【写作风格】
{voice}

【世界观设定】
{world}

【角色设定】
{chars}

【本章剧情大纲】
{ch_outline}

{custom_content}  <!-- 仅在这里插入你的素材，不改动原版 -->

【写作规则与禁止模式（原版完整保留）】
1. 严格遵循大纲，不偏离剧情
2. 保持人物性格一致，不OOC
3. 画面感强，多用感官描写（视觉/听觉/触觉）
4. 动作优先，情绪后置，禁止空洞抒情
5. 对话口语化，符合角色身份
6. 节奏紧凑，不水字数、不废话
7. 每章结尾必须留下强钩子
8. 禁止使用烂俗句式：电光火石之间、心中一凛、倒吸一口凉气、果不其然
9. 禁止AI模板化表达：眼睛微微一眯、嘴角勾起一抹弧度
10. 禁止被动语态，不用冗长修饰
11. 短段落、易阅读，符合网文排版

开始创作第{chapter_num}章正文：
"""

    print(f"正在生成第{chapter_num}章草稿...")
    content = call_llm(prompt, get_main_model(), max_tokens=4000, temperature=0.7)
    
    out_path = OUT_DIR / f"第{chapter_num}章_草稿.md"
    out_path.write_text(content, encoding="utf-8")
    print(f"✅ 第{chapter_num}章草稿已生成：{out_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("chapter", type=int, help="章节号")
    args = parser.parse_args()
    generate_draft(args.chapter)