#!/usr/bin/env python3
"""
角色注册表生成器 - 为基础阶段生成 characters.md 文件。
读取 seed.txt + voice.md + world.md + CRAFT.md，调用写作模型生成角色设定。
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
    调用写作模型生成角色设定内容。
    
    参数：
        prompt: 提示词字符串
        max_tokens: 生成的最大令牌数（默认16000）
    
    返回：
        生成的角色注册表文本
    """
    system_prompt = (
        "你是一位文学小说的角色设计师，精通创伤/欲望/需求/谎言框架、桑德森的三个滑块理论和对话独特性。"
        "你创造的角色感觉像真实的人，有矛盾、秘密和可识别的说话模式。"
        "你从不使用AI俗套词汇。请用中文写作，风格简洁直接。"
    )
    return call_llm(prompt, WRITER_MODEL, max_tokens, temperature=0.7, system=system_prompt)

seed = (BASE_DIR / "seed.txt").read_text()
world = (BASE_DIR / "world.md").read_text()

# Voice Part 2 only
voice = (BASE_DIR / "voice.md").read_text()
voice_lines = voice.split('\n')
part2_start = next(i for i, l in enumerate(voice_lines) if 'Part 2' in l)
voice_part2 = '\n'.join(voice_lines[part2_start:])

prompt = f"""为这部奇幻小说构建完整的角色注册表。这是 CHARACTERS.MD ——
关于故事中存在谁、什么驱动他们、他们如何说话以及他们背负什么秘密的权威参考。

种子概念：
{seed}

世界圣经（这些角色所处的世界）：
{world}

语音特征（小说的基调）：
{voice_part2}

角色塑造要求（来自 CRAFT.md）：

### 三个滑块（桑德森）
每个角色有三个独立的刻度（0-10）：
  主动性 -- 他们是推动剧情还是被动反应？
  亲和力 -- 读者是否同情他们？
  能力 -- 他们是否擅长自己做的事？
规则：引人入胜 = 至少两项高，或一项高且有明显成长。

### 创伤/欲望/需求/谎言框架
一个因果链：
  幽灵（背景事件）-> 创伤（持续的伤害）-> 谎言（用来应对的错误信念）
    -> 欲望（由谎言驱动的外部目标）-> 需求（内部真相，与谎言对立）
规则：欲望和需求必须处于张力中。谎言可以用一句话陈述。
  真相是其直接对立面。

### 对话独特性（8个维度）
1. 词汇水平  2. 句子长度  3. 缩略语/正式程度
4. 言语习惯  5. 提问与陈述比例  6. 打断模式
7. 比喻领域  8. 直接与间接
测试：移除对话标签。你能分辨是谁在说话吗？

构建至少包含以下角色的注册表：

1. **Cass Bellwright**（主角，POV角色）
   - 完整的创伤/欲望/需求/谎言链
   - 三个滑块及理由
   - 弧线类型（正/负/平）
   - 详细的说话模式（8个维度）
   - 身体习惯和不自觉的小动作
   - 至少2个秘密
   - 关键关系映射

2. **Eddan Bellwright**（父亲）
   - 与Cass同样深度
   - 他与密封日记的关系，颤抖的手
   - 他知道什么，隐藏什么

3. **Perin Bellwright**（兄弟）
   - 即使他大部分故事中缺席，也需要完整深度
   - Corda契约到底发生了什么
   - 通过缺席体现的存在感

4. **Maret Corda**（对手）
   - 不是反派——而是利益与Cass冲突的人
   - 她自己的创伤/欲望/需求/谎言（应该可以理解）

5. **Rector Suvaine**（学院院长）
   - 制度性对手——系统的化身
   - 她相信自己在保护Cantamura

6. **Torvald Hess**（联盟领袖）
   - 对系统的局外人视角
   - 他代表什么主题

7. **至少1-2个故事需要的额外角色**
   - Cass在学院的同伴/朋友？
   - Corda家族中认识Perin的人？
   - 一个忠诚分裂的宫廷歌手？

每个角色包括：
- 姓名、年龄、角色
- 幽灵/创伤/欲望/需求/谎言链（主要角色）
- 三个滑块（主动性/亲和力/能力）带数字和理由
- 弧线类型和轨迹
- 说话模式（所有8个维度，带示例台词）
- 外貌（具体，不俗套）
- 身体习惯和不自觉的小动作
- 秘密（读者不会立即知道的）
- 关键关系（映射到其他角色）
- 主题角色（这个角色体现什么问题？）

重要提示：
- 角色必须相互关联。他们的欲望应该相互冲突。
- 每个秘密都应该是如果揭示会改变故事的东西。
- 说话模式必须足够独特以通过无标签测试。
- 给Cass一些来自他天赋的习惯（疼痛、持续倾听）。
- 父亲颤抖的手应该与特定事物相关联。
- Maret Corda应该和Cass一样完整——一个值得的对手。
- 目标约3000-4000字。密集的角色塑造，不要冗余。
请用中文输出。
"""

if not API_KEY:
    print(f"错误：请先在 .env 中设置 {'DEEPSEEK_API_KEY' if API_PROVIDER == 'deepseek' else 'ANTHROPIC_API_KEY'}", file=sys.stderr)
    sys.exit(1)

print("正在调用写作模型...", file=sys.stderr)
result = call_writer(prompt)
print(result)
