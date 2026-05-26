#!/usr/bin/env python3
"""
seed.py -- 生成奇幻小说种子概念。

使用方法：
  uv run python seed.py              # 生成10个概念，选择一个
  uv run python seed.py --count=5    # 生成5个概念
  uv run python seed.py --riff "魔法需要记忆作为代价"  # 基于一个想法进行变体创作
"""

import argparse
import json
import os
import sys
from pathlib import Path

from api_client_1 import call_llm, get_writer_model, get_api_key, get_api_provider

BASE_DIR = Path(__file__).parent

WRITER_MODEL = get_writer_model()
API_KEY = get_api_key()
API_PROVIDER = get_api_provider()


def call_writer(prompt, max_tokens=4000):
    """
    调用写作模型生成内容。
    
    参数：
        prompt: 提示词字符串
        max_tokens: 生成的最大令牌数（默认4000）
    
    返回：
        生成的文本响应
    """
    system_prompt = (
        "你是一位精通奇幻文学的作家，熟读托尔金、勒古恩、罗斯福斯、沃尔夫、杰米辛等大师的作品。"
        "你能够生成独特、新颖且结构严谨的小说概念。你从不创作俗套的中世纪欧洲+精灵设定。"
        "每个概念都应该让读者惊叹：'我从未见过这样的故事！'请用中文输出。"
    )
    return call_llm(prompt, WRITER_MODEL, max_tokens, temperature=1.0, system=system_prompt)


GENERATE_PROMPT = """生成 {count} 个奇幻小说种子概念。每个概念都应该是一个完整的故事前提，可以据此构建一部小说。

对于每个概念，请提供：

序号. 标题（一个有感染力的暂定标题，而非俗套的名称）
钩子：一句话吸引读者拿起这本书。要具体、出人意料，不要用"在一个...的世界里..."
世界：这个世界有什么独特之处？不只是"有魔法"，而是这个地方的独特之处是什么？要具体——
  盐滩、倒置的塔楼、迁徙的城市、有记忆的海洋等等。要有感官冲击力。
魔法/代价：核心的奇幻元素是什么？使用它需要付出什么代价？根据桑德森第二法则，限制大于力量。
  代价应该创造有趣的困境。
张力：核心冲突是什么？必须既是个人的（一个角色的具体问题）又是宇宙性的（影响整个世界）。
  这两者必须相互对立。
主题：这个故事探讨什么问题？不是一个说教的信息——而是一个没有简单答案的真正问题。
为何独特：一句话说明这个概念与标准奇幻作品的不同之处。

在 {count} 个概念中追求多样性：
  - 至少一个非人类中心的世界
  - 至少一个更文学/安静而非史诗的故事
  - 至少一个叙事结构独特的概念
  - 至少一个设定在非典型欧洲风格背景的故事
  - 混合基调：黑暗、温暖、怪异、忧郁、奇幻

禁止生成：
  - 天选之子预言（除非以有趣的方式颠覆）
  - 黑暗领主/终极邪恶作为主要反派
  - 中世纪欧洲+精灵/矮人/兽人
  - "魔法学院"或"魔法学校"设定
  - 以三角恋为核心情节
"""

RIFF_PROMPT = """我有一个小说的种子想法：

"{idea}"

基于这个概念生成5个变体。保留核心想法中有趣的部分，但向不同方向推进。对于每个变体：

序号. 标题
钩子：一句话。
变化之处：你对原始种子做了什么改变？为什么？
世界：具体、感官化的世界细节。
魔法/代价：奇幻元素及其代价。
张力：个人+宇宙冲突。
主题：探讨的问题。

让这些变体真正有所不同——不要只是调整表面细节。改变主角、设定、基调、结构和主题焦点。
"""


def main():
    """
    主函数：生成奇幻小说种子概念。
    """
    parser = argparse.ArgumentParser(description="生成小说种子概念")
    parser.add_argument("--count", type=int, default=10,
                        help="生成概念的数量（默认：10）")    
    parser.add_argument("--riff", type=str, default=None,
                        help="基于现有想法进行变体创作")
    args = parser.parse_args()

    if not API_KEY:
        print(f"错误：请先在 .env 中设置 {'DEEPSEEK_API_KEY' if API_PROVIDER == 'deepseek' else 'ANTHROPIC_API_KEY'}")
        sys.exit(1)

    if args.riff:
        print(f"基于想法创作变体: {args.riff}\n")
        prompt = RIFF_PROMPT.format(idea=args.riff)
    else:
        print(f"正在生成 {args.count} 个种子概念...\n")
        prompt = GENERATE_PROMPT.format(count=args.count)

    result = call_writer(prompt, max_tokens=8000)
    print(result)
    print("\n" + "=" * 60)
    print("要选择一个种子，请将你喜欢的概念复制到 seed.txt 文件中：")
    print("  nano seed.txt")
    print("或者将多个概念混合成你自己的种子。")
    print("然后按照 WORKFLOW.md 中的步骤2继续。")


if __name__ == "__main__":
    main()
