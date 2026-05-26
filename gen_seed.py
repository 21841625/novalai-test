#!/usr/bin/env python3
"""
AI 灵感生成器 - 无灵感时用
自动生成网文选题 + 步步引导创作 + 自动生成 seed.txt
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
SEED_PATH = BASE_DIR / "seed.txt"

# 热门网文选题库
THEMES = [
    "无限流：主角无系统，靠智商破解恐怖副本",
    "都市悬疑：夜班保安，每晚遇到规则怪谈",
    "古风权谋：寒门书生，借情报网搅动朝堂",
    "科幻废土：机器人守护最后一个人类",
    "日常治愈：独居青年，收养一只会说话的猫",
    "玄幻逆袭：废柴少年，觉醒上古炼丹术",
    "规则怪谈：进入诡异学校，必须遵守校规活下去",
    "穿越历史：现代厨师，在古代靠美食称霸",
    "灵异探案：能看见鬼魂的警察，破解悬案",
    "克苏鲁：图书馆管理员，发现古籍里的异世界秘密"
]

def generate_seed():
    print("="*50)
    print("📝 AutoNovel AI 灵感生成器")
    print("="*50)
    
    # 1. 展示选题
    print("\n🔥 为你推荐10个热门网文选题：")
    for i, t in enumerate(THEMES, 1):
        print(f"{i}. {t}")

    # 2. 选择选题
    while True:
        try:
            choice = int(input("\n请选择你喜欢的选题（输入数字1-10）："))
            if 1 <= choice <= 10:
                break
        except:
            print("输入错误，请输入1-10的数字")
    selected = THEMES[choice-1]
    print(f"\n✅ 你选择了：{selected}")

    # 3. 引导补充细节
    print("\n🎯 接下来简单补充2个细节（直接回车用默认值）：")
    character = input("1. 主角设定（默认：普通打工人）：") or "普通打工人"
    hook = input("2. 核心看点/钩子（默认：硬核智商流）：") or "硬核智商流"

    # 4. 自动生成 seed 文本
    seed_content = f"{selected}，主角是{character}，核心风格：{hook}，节奏紧凑，无俗套模板"
    
    # 5. 保存为 seed.txt
    with open(SEED_PATH, "w", encoding="utf-8") as f:
        f.write(seed_content)
    
    print("\n🎉 灵感种子生成完成！")
    print(f"📄 生成内容：{seed_content}")
    print(f"💾 文件位置：{SEED_PATH}")
    print("\n👉 现在直接运行：python run_pipeline.py 即可开始全自动创作！")

if __name__ == "__main__":
    generate_seed()