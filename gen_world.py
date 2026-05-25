#!/usr/bin/env python3
"""
世界设定生成器 - 为基础阶段生成 world.md 文件。
读取 seed.txt + voice.md + CRAFT.md，调用写作模型生成世界设定。
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
    调用写作模型生成世界设定内容。
    
    参数：
        prompt: 提示词字符串
        max_tokens: 生成的最大令牌数（默认16000）
    
    返回：
        生成的世界设定文本
    """
    system_prompt = (
        "你是一位文学奇幻世界构建师。你创造丰富、具体的世界，具有内部一致性、感官细节和主题共鸣。"
        "你从不使用俗套的'中世纪奇幻'陈词滥调。你的世界感觉真实可触，并对故事产生影响。"
        "请用中文写作，风格简洁直接。"
    )
    return call_llm(prompt, WRITER_MODEL, max_tokens, temperature=0.7, system=system_prompt)

seed = (BASE_DIR / "seed.txt").read_text()
voice = (BASE_DIR / "voice.md").read_text()
craft = (BASE_DIR / "CRAFT.md").read_text()

# Voice Part 2 only
voice_lines = voice.split('\n')
part2_start = next(i for i, l in enumerate(voice_lines) if 'Part 2' in l)
voice_part2 = '\n'.join(voice_lines[part2_start:])

prompt = f"""为这部奇幻小说构建完整的世界设定圣经。这是 WORLD.MD ——
关于故事中存在什么、魔法如何运作、地理、派系、历史和文化规范的权威参考。

种子概念：
{seed}

语音特征（小说的基调）：
{voice_part2}

世界构建要求（来自 CRAFT.md）：

### 魔法系统规则（桑德森第一法则）
- 限制比力量更有趣
- 每一次使用都有代价或后果
- 魔法应以有趣的方式解决问题，而不仅仅是"让事情发生"
- 系统必须内部一致

### 世界构建层次
1. 地理：具有感官细节的特定地点
2. 历史：塑造现在的事件
3. 政治：谁掌握权力，为什么
4. 文化：习俗、传统、禁忌、艺术、宗教
5. 经济：人们重视什么？如何生存？
6. 魔法：超自然的规则和代价

用以下章节构建世界圣经：

1. **标题与一句话简介**
   - 这个世界/设定的名称
   - 一句话概括其精髓

2. **地理**
   - 地图描述（关键地点、地形、气候）
   - 至少5个有特定目的的命名地点
   - 地理如何塑造文化和冲突

3. **历史**
   - 关键事件时间线（至少最近50-100年）
   - 关键时刻的"之前"和"之后"
   - 过去未解决的紧张关系

4. **魔法系统**
   - 它能做什么？有什么限制？
   - 代价是什么？（身体、情感、社会）
   - 谁可以使用它？为什么？
   - 文化对魔法的态度

5. **派系与权力结构**
   - 至少4个目标冲突的主要派系
   - 维持秩序（或混乱）的机构
   - 隐藏的权力和幕后玩家

6. **文化与社会**
   - 不同阶层的日常生活
   - 习俗、仪式、节日
   - 禁忌及其被打破时的后果
   - 主角将打破的"常态"

7. **主题共鸣**
   - 这个世界如何强化故事的主题？
   - 世界中的哪些矛盾创造了叙事张力？

重要提示：
- 目标约4000-5000字。密集、具体的世界构建，不要冗余。
- 每个细节都应为故事服务——不要为了世界构建而构建。
- 做出能为角色创造有趣困境的选择。
- 用感官细节奠定一切：气味、声音、质感。
- 避免俗套的奇幻元素。让这个世界感觉独特。
请用中文输出。
"""

if not API_KEY:
    print(f"错误：请先在 .env 中设置 {'DEEPSEEK_API_KEY' if API_PROVIDER == 'deepseek' else 'ANTHROPIC_API_KEY'}", file=sys.stderr)
    sys.exit(1)

print("正在调用写作模型...", file=sys.stderr)
result = call_writer(prompt)
print(result)
