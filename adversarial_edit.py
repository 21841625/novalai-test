#!/usr/bin/env python3
"""
对抗性编辑：让评判模型从每章中删减500字。
被删减的内容揭示了最薄弱的部分。删减列表即是修订计划。

使用方法：python adversarial_edit.py 1        # 单章编辑
          python adversarial_edit.py all      # 所有章节
"""
import os
import sys
import json
import re
from pathlib import Path

from api_client import call_llm, get_judge_model, get_api_key, get_api_provider

BASE_DIR = Path(__file__).parent
CHAPTERS_DIR = BASE_DIR / "chapters"
EDIT_LOG_DIR = BASE_DIR / "edit_logs"
EDIT_LOG_DIR.mkdir(exist_ok=True)

JUDGE_MODEL = get_judge_model()
API_KEY = get_api_key()
API_PROVIDER = get_api_provider()

def call_judge(prompt, max_tokens=8000):
    """
    调用评判模型进行对抗性编辑分析。
    
    参数：
        prompt: 提示词字符串
        max_tokens: 生成的最大令牌数（默认8000）
    
    返回：
        生成的分析结果文本
    """
    system_prompt = (
        "你是一位严苛的文学编辑。你删减散文中的冗余内容。"
        "你对尚可的句子毫不留情——如果一个句子没有存在的价值，它就该被删除。"
        "你精确引用原文。你从不编造或释义。始终用有效的JSON格式响应。"
    )
    return call_llm(prompt, JUDGE_MODEL, max_tokens, temperature=0.3, system=system_prompt)

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
        start = text.find('[')
    if start == -1:
        raise ValueError("未找到JSON")
    # 首先尝试直接解析
    try:
        return json.loads(text[start:], strict=False)
    except json.JSONDecodeError:
        # 查找匹配的括号
        depth = 0
        in_string = False
        escape = False
        open_char = text[start]
        close_char = '}' if open_char == '{' else ']'
        for i in range(start, len(text)):
            c = text[i]
            if escape:
                escape = False
                continue
            if c == '\\' and in_string:
                escape = True
                continue
            if c == '"' and not escape:
                in_string = not in_string
                continue
            if in_string:
                continue
            if c == open_char:
                depth += 1
            elif c == close_char:
                depth -= 1
                if depth == 0:
                    return json.loads(text[start:i+1], strict=False)
        return json.loads(text[start:], strict=False)

EDIT_PROMPT = """你正在编辑一部奇幻小说的章节。你的任务：准确找出需要删减或重写的内容，使本章更紧凑、更锐利、更生动。

本章内容（{word_count} 字）：
{chapter_text}

你的任务：
1. 找出10-20个应该删减或重写的具体段落。
   对于每个段落，引用确切文本（至少10个字以确保明确），解释为什么它薄弱，并进行分类。

2. 将每个删减内容分类为以下之一：
   - FAT（脂肪）：无任何贡献，可以移除而无损失
   - REDUNDANT（冗余）：重复之前句子/场景已经展示的内容
   - OVER-EXPLAIN（过度解释）：叙述者解释场景已经展示的内容
   - GENERIC（通用）：可能出现在任何小说中，不特定于这个世界/角色
   - TELL（讲述）：命名情感或状态而非展示它
   - STRUCTURAL（结构）：破坏节奏或韵律的段落/章节

3. 对于需要重写的内容（非删减），提供具体的修订版本。

4. 估算总共可以删减多少字而不损失本章需要的任何内容。

用JSON格式响应：
{{
  "cuts": [
    {{
      "quote": "从本章中引用的确切文本（10字以上）",
      "type": "FAT|REDUNDANT|OVER-EXPLAIN|GENERIC|TELL|STRUCTURAL",
      "reason": "为什么应该删除",
      "action": "CUT 或 REWRITE",
      "rewrite": "如果action是REWRITE则提供替换文本，如果是CUT则为null"
    }}
  ],
  "total_cuttable_words": N,
  "tightest_passage": "引用本章中最好的2-3句话——你永远不会改动的句子",
  "loosest_passage": "引用最差的2-3句话——最需要改进的句子",
  "overall_fat_percentage": N,
  "one_sentence_verdict": "本章做得好的地方和拖后腿的地方，用一句话概括"
}}
"""

def edit_chapter(ch_num):
    """
    编辑指定章节，分析需要删减或重写的内容。
    
    参数：
        ch_num: 章节号
    
    返回：
        (分析结果, 章节字数)
    """
    ch_path = CHAPTERS_DIR / f"ch_{ch_num:02d}.md"
    text = ch_path.read_text()
    word_count = len(text.split())
    
    prompt = EDIT_PROMPT.format(chapter_text=text, word_count=word_count)
    raw = call_judge(prompt)
    result = parse_json(raw)
    
    # 保存日志
    log_path = EDIT_LOG_DIR / f"ch{ch_num:02d}_cuts.json"
    with open(log_path, "w") as f:
        json.dump(result, f, indent=2)
    
    return result, word_count

def main():
    """
    主函数：执行对抗性编辑分析。
    """
    if len(sys.argv) < 2:
        print("使用方法：python adversarial_edit.py <章节号|all>")
        sys.exit(1)
    
    if sys.argv[1] == "all":
        chapters = list(range(1, 25))
    else:
        chapters = [int(sys.argv[1])]
    
    for ch in chapters:
        print(f"\n{'='*50}")
        print(f"正在编辑第 {ch} 章")
        print(f"{'='*50}")
        
        try:
            result, wc = edit_chapter(ch)
        except Exception as e:
            print(f"  错误: {e}")
            continue
        
        cuts = result.get("cuts", [])
        cuttable = result.get("total_cuttable_words", 0)
        fat_pct = result.get("overall_fat_percentage", 0)
        verdict = result.get("one_sentence_verdict", "")
        
        # 按类型统计
        type_counts = {}
        for c in cuts:
            t = c.get("type", "?")
            type_counts[t] = type_counts.get(t, 0) + 1
        
        print(f"  字数: {wc}")
        print(f"  找到的删减点: {len(cuts)}")
        print(f"  可删减字数: ~{cuttable} ({fat_pct}% 冗余)")
        print(f"  按类型统计: {type_counts}")
        print(f"  评价: {verdict}")
        print(f"  最紧凑段落: {result.get('tightest_passage', '')[:100]}...")
        print(f"  最松散段落: {result.get('loosest_passage', '')[:100]}...")

if __name__ == "__main__":
    main()
