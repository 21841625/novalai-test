#!/usr/bin/env python3
"""
大纲生成器 - 从种子概念、世界设定、角色、谜团和写作技巧生成 outline.md 文件。
"""     
import os
import sys
from pathlib import Path

from api_client import call_llm, get_writer_model, get_api_key, get_api_provider

BASE_DIR = Path(__file__).parent

WRITER_MODEL = get_writer_model()
API_KEY = get_api_key()
API_PROVIDER = get_api_provider()

def call_writer(prompt, max_tokens=16000):
    """
    调用写作模型生成章节大纲内容。
    
    参数：
        prompt: 提示词字符串
        max_tokens: 生成的最大令牌数（默认16000）
    
    返回：
        生成的大纲文本
    """
    system_prompt = (
        "你是一位小说架构师，精通Save the Cat节拍、桑德森的情节原则、Dan Harmon的故事圈和MICE商数。"
        "你构建的大纲让作者可以直接起草，无需临时发明结构。每章都有节拍、情感弧线和尝试-失败循环类型。"
        "你从不使用AI俗套词汇。请用中文写作，风格简洁直接。"
    )
    return call_llm(prompt, WRITER_MODEL, max_tokens, temperature=0.5, system=system_prompt)

seed = (BASE_DIR / "seed.txt").read_text()
world = (BASE_DIR / "world.md").read_text()
characters = (BASE_DIR / "characters.md").read_text()
mystery = (BASE_DIR / "MYSTERY.md").read_text()
craft = (BASE_DIR / "CRAFT.md").read_text()

# Voice Part 2 only
voice = (BASE_DIR / "voice.md").read_text()
voice_lines = voice.split('\n')
part2_start = next(i for i, l in enumerate(voice_lines) if 'Part 2' in l)       
voice_part2 = '\n'.join(voice_lines[part2_start:])

prompt = f"""为这部奇幻小说构建完整的章节大纲。目标：22-26章，总计约80,000字（每章约3,000-4,000字）。

种子概念：
{seed}

核心谜团（仅供作者参考——读者逐步发现）：
{mystery}

世界圣经：
{world}

角色注册表：
{characters}

语音（基调和语域）：
{voice_part2}

写作技巧参考（遵循的结构）：
{craft}

构建大纲包含：

## 幕结构
规划第一幕（0-23%）、第二幕第一部分（23-50%）、第二幕第二部分（50-77%）、第三幕（77-100%）。
说明关键节点的百分比标记。

## 章节大纲

每章提供：
### Ch N: [标题]
- **POV:**（始终是Cass，第三人称有限视角）
- **地点:** 哪些区域/位置
- **Save the Cat节拍:** 本章服务于哪个节拍（开场画面、铺垫、催化剂等）
- **%标记:** 在小说中的位置
- **情感弧线:** 起始情感 -> 结束情感
- **尝试-失败循环:** 是但 / 否且 / 否但 / 是且
- **节拍:** 3-5个必须发生的具体场景节拍
- **伏笔:** 本章植入的伏笔元素
- **回收:** 在本章回收的伏笔元素
- **角色发展:** 章节结束时Cass（或其他角色）发生什么变化
- **谎言:** Cass的谎言（"如果我掌握了系统，我可以从内部解决问题"）在本章如何被强化或挑战
- **~字数目标:** 用于节奏控制

## 伏笔记录

追踪每个植入线索的表格：
| 线索 | 植入（章节） | 强化（章节） | 回收（章节） | 类型 |

至少包含15条线索。类型：物品、对话、动作、象征、结构。

关键情节架构：

第一幕（第1-6章左右）：建立Cass的世界、他的痛苦、他的天赋、学院、他的家庭。
尽早植入谜团（锁着的房间、被禁止的钟声、父亲的颤抖）。催化剂：某事迫使Cass调查Perin的契约。

第二幕第一部分（第7-12章左右）：调查。Cass深入Corda契约，遇到Maret，与Torvald和Lenne结盟，开始更清晰地听到和声。

第二幕第二部分（第13-18章左右）：压力加剧。Maret对Bellwright家族采取行动。父亲的秘密开始浮出水面。Cass的谎言越来越难以维持。
全失点：Cass与父亲对质，了解全部真相。

第三幕（第19-24章左右）：Cass理解了问题。必须选择如何回答。高潮使用既定的音调法则间隔展开。结局展示他选择的后果。

约束条件：
- 高潮必须能够使用既定的音调法则间隔机械解决
- Cass的调查应该感觉像一个悬疑情节叠加在成长弧线上
- 稳定陷阱：坏事必须保持坏。并非一切都能干净解决。
- Perin必须在某个时刻亲自出现（不仅仅是在记忆/信件中）
- 至少3章应该是"安静的"——以角色为中心，低动作，情感丰富
- 变化尝试-失败类型：60%+应该是"是但"或"否且"
- 伏笔记录必须有至少3章的伏笔到回收距离
请用中文输出。
"""

if not API_KEY:
    print(f"错误：请先在 .env 中设置 {'DEEPSEEK_API_KEY' if API_PROVIDER == 'deepseek' else 'ANTHROPIC_API_KEY'}", file=sys.stderr)
    sys.exit(1)

print("正在调用写作模型...", file=sys.stderr)
result = call_writer(prompt)
print(result)
