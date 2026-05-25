#!/usr/bin/env python3
"""
章节比较排名：将章节两两配对进行比较。
评判模型选择获胜者并引用决定性时刻。
通过循环赛制生成真实的排名顺序。

使用方法：python compare_chapters.py          # 完整锦标赛
          python compare_chapters.py 1 10     # 单次对决
"""
import os
import sys
import json
import re
import random
from pathlib import Path
from datetime import datetime

from api_client import call_llm, get_judge_model, get_api_key, get_api_provider

BASE_DIR = Path(__file__).parent
CHAPTERS_DIR = BASE_DIR / "chapters"

JUDGE_MODEL = get_judge_model()
API_KEY = get_api_key()
API_PROVIDER = get_api_provider()

def call_judge(prompt, max_tokens=4000):
    """
    调用评判模型进行章节比较。
    
    参数：
        prompt: 提示词字符串
        max_tokens: 生成的最大令牌数（默认4000）
    
    返回：
        生成的比较结果文本
    """
    system_prompt = (
        "你是一位文学编辑，正在比较同一部小说的两章。"
        "你选择更好的一章。不允许平局。"
        "你引用具体段落来证明你的选择。"
        "仅用有效的JSON格式响应。"
    )
    return call_llm(prompt, JUDGE_MODEL, max_tokens, temperature=0.2, system=system_prompt)

def parse_json(text):
    """
    解析JSON响应，处理代码块标记和不完整的JSON。
    
    参数：
        text: 包含JSON的文本
    
    返回：
        解析后的JSON对象
    
    抛出：
        ValueError: 如果未找到JSON
    """
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r'^```\w*\n?', '', text)
        text = re.sub(r'\n?```$', '', text)
    start = text.find('{')
    if start == -1:
        raise ValueError("未找到JSON")
    try:
        return json.loads(text[start:], strict=False)
    except json.JSONDecodeError:
        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(text)):
            c = text[i]
            if escape: escape = False; continue
            if c == '\\' and in_string: escape = True; continue
            if c == '"' and not escape: in_string = not in_string; continue
            if in_string: continue
            if c == '{': depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    return json.loads(text[start:i+1], strict=False)
        return json.loads(text[start:], strict=False)

COMPARE_PROMPT = """比较同一部奇幻小说的这两章。
两者都是初稿。选择更好的一章。你必须选择一个获胜者——不允许平局。

章节A (第{ch_a}章):
{text_a}

章节B (第{ch_b}章):
{text_b}

从以下维度进行比较：
- 哪一章的散文更锐利（更具体，更少通用）？
- 哪一章的对话更好（听起来像说话，不是书面散文）？
- 哪一章创造了更多真正的紧张感或惊喜？
- 哪一章更信任读者（更少过度解释）？
- 哪一章的AI写作模式更少？

你必须选择一个。如果它们很接近，选择有最佳时刻的那一章——你希望自己写的句子。

用JSON格式响应：
{{
  "winner": "A" 或 "B",
  "winner_chapter": N,
  "margin": "clear" 或 "slight" 或 "razor-thin",
  "decisive_moment": "引用决定胜负的段落——来自获胜者",
  "winner_strength": "获胜者做了什么而失败者没有做",
  "loser_weakness": "具体是什么拖垮了失败者",
  "best_sentence_a": "引用A中最好的一句话",
  "best_sentence_b": "引用B中最好的一句话"
}}
"""

def compare(ch_a, ch_b):
    """
    比较两章内容。
    
    参数：
        ch_a: 章节A的编号
        ch_b: 章节B的编号
    
    返回：
        比较结果JSON对象
    """
    text_a = (CHAPTERS_DIR / f"ch_{ch_a:02d}.md").read_text()
    text_b = (CHAPTERS_DIR / f"ch_{ch_b:02d}.md").read_text()
    
    # 截断到约3000字以适应上下文限制
    words_a = text_a.split()
    words_b = text_b.split()
    if len(words_a) > 3000:
        text_a = ' '.join(words_a[:3000]) + "\n[已截断]"
    if len(words_b) > 3000:
        text_b = ' '.join(words_b[:3000]) + "\n[已截断]"
    
    prompt = COMPARE_PROMPT.format(
        ch_a=ch_a, ch_b=ch_b,
        text_a=text_a, text_b=text_b
    )
    raw = call_judge(prompt)
    result = parse_json(raw)
    result["ch_a"] = ch_a
    result["ch_b"] = ch_b
    return result

def run_tournament(chapters):
    """
    运行瑞士制锦标赛：按相似的Elo分数配对，运行足够轮数来排名。
    
    参数：
        chapters: 章节编号列表
    
    返回：
        (排名列表, Elo评分字典, 对决结果列表)
    """
    # 初始化Elo评分
    elo = {ch: 1500 for ch in chapters}
    K = 32
    matchups = []
    
    # 运行3-4轮瑞士配对
    n_rounds = 4
    for round_num in range(n_rounds):
        # 按Elo排序，相邻配对
        ranked = sorted(chapters, key=lambda c: elo[c], reverse=True)
        pairs = []
        used = set()
        for i in range(0, len(ranked) - 1, 2):
            a, b = ranked[i], ranked[i+1]
            if (a, b) not in used and (b, a) not in used:
                pairs.append((a, b))
                used.add((a, b))
        
        print(f"\n--- 第 {round_num + 1} 轮 ({len(pairs)} 场对决) ---")
        for ch_a, ch_b in pairs:
            try:
                result = compare(ch_a, ch_b)
                winner = result.get("winner_chapter", result.get("winner"))
                margin = result.get("margin", "?")
                
                # 处理 "A"/"B" 与章节号的转换
                if winner == "A":
                    winner = ch_a
                elif winner == "B":
                    winner = ch_b
                else:
                    winner = int(winner)
                
                loser = ch_b if winner == ch_a else ch_a
                
                # 更新Elo评分
                exp_a = 1 / (1 + 10 ** ((elo[ch_b] - elo[ch_a]) / 400))
                score_a = 1.0 if winner == ch_a else 0.0
                elo[ch_a] += K * (score_a - exp_a)
                elo[ch_b] += K * ((1 - score_a) - (1 - exp_a))
                
                result["winner_resolved"] = winner
                matchups.append(result)
                
                print(f"  第{ch_a}章 vs 第{ch_b}章: 获胜者=第{winner}章 ({margin})")
                
            except Exception as e:
                print(f"  第{ch_a}章 vs 第{ch_b}章: 错误 ({e})")
    
    # 最终排名
    ranking = sorted(chapters, key=lambda c: elo[c], reverse=True)
    
    return ranking, elo, matchups

def main():
    """
    主函数：执行章节比较。
    """
    if len(sys.argv) == 3:
        # 单次对决
        ch_a, ch_b = int(sys.argv[1]), int(sys.argv[2])
        result = compare(ch_a, ch_b)
        print(json.dumps(result, indent=2))
    else:
        # 完整锦标赛
        chapters = list(range(1, 25))
        ranking, elo, matchups = run_tournament(chapters)
        
        print(f"\n{'='*50}")
        print("最终排名")
        print(f"{'='*50}")
        for i, ch in enumerate(ranking):
            print(f"  {i+1:2d}. 第{ch:2d}章  (Elo: {elo[ch]:.0f})")
        
        # 保存结果
        results = {
            "ranking": ranking,
            "elo": {str(k): round(v) for k, v in elo.items()},
            "matchups": matchups,
            "timestamp": datetime.now().isoformat()
        }
        out_path = BASE_DIR / "edit_logs" / "tournament_results.json"
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n已保存到 {out_path}")

if __name__ == "__main__":
    main()
