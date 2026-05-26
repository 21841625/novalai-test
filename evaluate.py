#!/usr/bin/env python3
"""
使用评估模型对小说或其组成部分进行评估。

使用方法:
  python evaluate.py --phase foundation    # 评估规划文档
  python evaluate.py --chapter 1          # 评估第1章
  python evaluate.py --full               # 评估完整小说
"""
import os
import sys
import json
import re
import argparse
from pathlib import Path
from datetime import datetime

from api_client import call_llm, get_judge_model, get_api_key, get_api_provider

# 基础目录
BASE_DIR = Path(__file__).parent

# 获取评估模型、API密钥和提供商
JUDGE_MODEL = get_judge_model()
API_KEY = get_api_key()
API_PROVIDER = get_api_provider()

# 目录定义
CHAPTERS_DIR = BASE_DIR / "chapters"  # 章节文件目录
EVAL_LOG_DIR = BASE_DIR / "eval_logs"  # 评估日志目录
EVAL_LOG_DIR.mkdir(exist_ok=True)  # 确保日志目录存在

# 规划文档评估提示词
FOUNDATION_PROMPT = """评估这份奇幻小说规划文档的质量。

风格指南文档 (VOICE DOC):
{voice}

世界设定手册 (WORLD BIBLE):
{world}

人物设定 (CHARACTERS):
{characters}

大纲 (OUTLINE):
{outline}

请基于以下标准评估每份文档：
1. 风格指南 (VOICE)：风格是否具体且可落地？是否提供了具体的写作指导？
   是否有明确的"禁用清单"（禁止使用的词汇/句式）？语气是否独特？
   
2. 世界设定 (WORLD)：世界设定是否足够详细以支撑写作？是否有明确的规则
   和约束？是否有足够的细节支撑感官描写？
   关键地点及其重要性是否清晰？

3. 人物设定 (CHARACTERS)：人物是否有鲜明的辨识度？是否有独特的说话方式？
   人物是否有明确的欲望和缺陷（能制造冲突）？主角是否有吸引力？

4. 大纲 (OUTLINE)：是否有清晰的三幕式结构？人物成长弧光是否可见？
   是否埋设了伏笔？章节篇幅是否合理？

为每个维度打分（0-10分）。并提供具体的改进建议。

请以JSON格式回复：
{{
  "voice": {{"score": N, "weakest": "具体缺陷", "fix": "可落地的改进建议", "note": "补充说明"}},
  "world": {{"score": N, "weakest": "...", "fix": "...", "note": "..."}},
  "characters": {{"score": N, "weakest": "...", "fix": "...", "note": "..."}},
  "outline": {{"score": N, "weakest": "...", "fix": "...", "note": "..."}},
  "overall_score": N,
  "top_3_gaps": ["主要问题1", "主要问题2", "主要问题3"],
  "ready_to_write": true/false
}}
"""


def call_judge(prompt, max_tokens=8000):
    """调用评估模型"""
    return call_llm(prompt, JUDGE_MODEL, max_tokens, temperature=0.2)


def parse_json_response(raw):
    """从可能格式不规范的响应中提取JSON内容"""
    try:
        # 查找JSON块的起始和结束位置
        json_start = raw.find("{")
        json_end = raw.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            return json.loads(raw[json_start:json_end])
    except Exception as e:
        # 解析失败时捕获异常
        pass
    return {"raw": raw[:500]}  # 返回原始内容的前500个字符


def slop_score(text):
    """对AI写作常见的不良模式进行机械检查"""
    slop_penalty = 0.0  # 劣质写作惩罚分
    
    # 检查重复词汇/短语
    words = text.lower().split()
    repeated = sum(1 for i in range(len(words)-2) if words[i] == words[i+1])
    if repeated > 3:
        slop_penalty += 0.5
    
    # 检查被动语态使用频率
    passive_count = len(re.findall(r'\b(被|被人|由)\b.*?\b(了|过)\b', text))
    if passive_count > 10:
        slop_penalty += 0.3
    
    # 检查"一种...的感觉"这类模板化表达
    if text.count("一种") > 6 and text.count("的感觉") > 3:
        slop_penalty += 0.2
    
    # 检查模糊修饰词
    vague_count = sum(text.count(w) for w in ["非常", "十分", "相当", "有点"])
    if vague_count > 15:
        slop_penalty += 0.3
    
    # 检查句子长度是否过于单一
    sentences = re.split(r'[。！？]+', text)
    lens = [len(s.split()) for s in sentences if len(s) > 10]
    if len(lens) > 20:
        avg_len = sum(lens) / len(lens)
        if all(abs(len(s.split()) - avg_len) < 5 for s in sentences if len(s) > 10):
            slop_penalty += 0.4
    
    return {
        "slop_penalty": round(slop_penalty, 2),
        "repeated_words": repeated,
        "passive_instances": passive_count,
        "sense_of_count": text.count("一种") + text.count("的感觉"),
        "vague_modifiers": vague_count
    }


def load_layer_files():
    """加载所有规划文档"""
    layers = {}
    for name in ["voice", "world", "characters", "outline", "canon"]:
        path = BASE_DIR / f"{name}.md"
        layers[name] = path.read_text(encoding="utf-8") if path.exists() else "(未找到)"
    return layers


def load_chapter(num):
    """加载单个章节内容"""
    path = CHAPTERS_DIR / f"ch_{num:02d}.md"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def load_all_chapters():
    """加载所有章节，返回字典 {章节号: 文本内容}"""
    chapters = {}
    for path in sorted(CHAPTERS_DIR.glob("ch_*.md")):
        match = re.match(r'ch_(\d+)\.md', path.name)
        if match:
            chapters[int(match.group(1))] = path.read_text(encoding="utf-8")
    return chapters


def evaluate_foundation():
    """评估规划文档"""
    layers = load_layer_files()
    
    prompt = FOUNDATION_PROMPT.format(
        voice=layers["voice"],
        world=layers["world"],
        characters=layers["characters"],
        outline=layers["outline"],
    )
    raw = call_judge(prompt)
    result = parse_json_response(raw)
    return result


# --- 章节评估模块 ---

CHAPTER_PROMPT = """基于规划文档评估本章内容。

风格定义（第二部分为行文风格）:
{voice}

世界设定手册:
{world}

人物设定表:
{characters}

官方设定（硬性事实）:
{canon}

本章大纲条目:
{chapter_outline}

上一章结尾内容:
{prev_chapter_tail}

本章文本:
{chapter_text}

请评估以下9个维度：

1. 风格一致性：行文风格与风格定义的匹配度？
   检查句式变化、词汇选择、"先行动后情绪"原则、语气是否符合要求。

2. 情节节点覆盖：是否覆盖了大纲中的所有情节节点？
   情节节点是通过场景戏剧化呈现，还是仅简单提及？

3. 人物语言风格：对话是否有辨识度？每个人物的说话方式是否独特？
   卡西（Cass）的语气是否符合14岁少女的设定？

4. 伏笔埋设：伏笔是否自然融入？既不过于明显，也不模糊到无法察觉。

5. 行文质量：句式多样性、细节丰富度、基于人物经历的隐喻使用、
   情绪高潮处的"展示而非告知"原则执行情况。

6. 叙事连贯性：是否与上一章逻辑衔接？不仅是情节连贯，也包括情绪连贯。

7. 设定合规性：核对所有事实是否符合官方设定。列出违规点。

8. 世界观融合：本章中世界观是否起到实际作用，还是仅作为背景板？

9. 阅读吸引力：读者是否有继续阅读的欲望？是否有惊喜感？
   即使是优秀但完全可预测的内容，也缺乏吸引力。

评分标准（0-10分）:
- 0-3分：重大问题，需要完全重写
- 4-5分：显著缺陷，需要大幅修改
- 6分：中等AI生成章节 - 合格但无亮点
- 7分：良好 - 执行到位，仅有小问题
- 8分：优秀 - 几乎无缺点，有出彩的瞬间
- 9分：卓越 - 全篇写作技巧出色
- 10分：完美（初稿不可能达到）

各维度专项问题：

1. 风格一致性：行文是否符合voice.md第二部分的要求？检查：
   句式节奏变化、词汇选择、"先行动后情绪"原则、指定的语气风格。
   引用最符合风格的片段 AND 最不符合的片段。
   是否有任何段落呈现出通用奇幻小说的模板化风格（可出现在任何小说中）？
   若有，最高分不超过7分。

2. 情节节点覆盖：是否覆盖了大纲中的所有情节节点？情节节点是戏剧化呈现
   还是仅简单提及？仅用一句话概括的情节节点按半覆盖计算。
   分数反映情节节点的执行质量，而非仅看是否存在。

3. 人物语言风格：隐去所有对话标签后，能否区分说话人？
   人物是否有雷同的说话方式？对话读起来像书面语还是自然口语？
   卡西的语气是否符合特定14岁少女的设定，还是只是"通用年轻主角"？
   人物是否有说出令人意外的话——不只是正确的话，而是真实的、符合性格的话？
   从不结巴、犹豫或说错话的人物是典型的AI写作模式。

4. 伏笔埋设：伏笔是否自然融入？过于明显的伏笔不如完全隐藏的伏笔。
   分数基于伏笔的融合度，而非仅看是否存在。

5. 行文质量：句式多样性（检查：是否有3个以上连续句子以相同方式开头？）。
   细节丰富度（具象名词优于抽象名词）。
   基于卡西经历的隐喻（而非词典式的通用隐喻）。
   情绪高潮处的"展示而非告知"。
   引用最差的句子并解释原因。同时检查：
   重复短语、过度使用的句式、可删除且不影响内容的段落。

6. 叙事连贯性：是否与上一章逻辑衔接？不仅是情节连贯，也包括人物情绪状态的连贯。
   人物的心理状态是否符合前文设定？

7. 设定合规性：核对所有事实是否符合官方设定。列出违规点。
   单次重大违规将最高分数限制为6分。检查项：
   人物姓名、地点、魔法系统规则、时间线、已设定事件、外貌描述。

8. 世界观融合：本章中世界观是否起到实际作用，还是仅作为背景板？
   若场景只需替换专有名词就能适用于任何奇幻小说，最高分不超过5分。

9. 阅读吸引力：读者是否有翻页的欲望？张力来自何处——情节、人物、悬念还是行文？
   是否有令人惊喜的瞬间？
   仅当章节有出人意料的内容时，才可给出8分及以上。

请以JSON格式回复：
{{
  "voice_adherence": {{"score": N, "weakest_moment": "引用具体的糟糕片段", "fix": "改进建议", "note": "补充说明"}},
  "beat_coverage": {{"score": N, "weakest_moment": "...", "fix": "...", "note": "..."}},
  "character_voice": {{"score": N, "weakest_moment": "...", "fix": "...", "note": "..."}},
  "plants_seeded": {{"score": N, "weakest_moment": "...", "fix": "...", "note": "..."}},
  "prose_quality": {{"score": N, "weakest_sentence": "引用该句子", "fix": "改写建议", "strongest_sentence": "引用该句子", "note": "..."}},
  "continuity": {{"score": N, "note": "..."}},
  "canon_compliance": {{"score": N, "violations": ["违规点1", "违规点2"], "note": "..."}},
  "lore_integration": {{"score": N, "weakest_moment": "...", "fix": "...", "note": "..."}},
  "engagement": {{"score": N, "surprise_moment": "引用惊喜片段（若无则填无）", "fix": "...", "note": "..."}},
  "overall_score": N,
  "slop_check": {{}},
  "ready_to_revise": true/false
}}
"""

# 补充原代码缺失的命令行参数解析和主函数（保证文件完整性）
def main():
    """主函数：解析命令行参数并执行对应评估"""
    parser = argparse.ArgumentParser(description="小说评估工具")
    parser.add_argument("--phase", choices=["foundation"], help="评估规划文档阶段")
    parser.add_argument("--chapter", type=int, help="评估指定章节号")
    parser.add_argument("--full", action="store_true", help="评估完整小说")
    
    args = parser.parse_args()
    
    # 记录评估时间
    eval_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 根据参数执行不同评估
    if args.phase == "foundation":
        print("开始评估规划文档...")
        result = evaluate_foundation()
        # 保存评估结果
        log_path = EVAL_LOG_DIR / f"foundation_eval_{eval_time}.json"
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"规划文档评估完成，结果已保存至: {log_path}")
        
    elif args.chapter:
        print(f"开始评估第 {args.chapter} 章...")
        # 此处需补充章节评估的具体逻辑（原代码片段未完成）
        chapter_text = load_chapter(args.chapter)
        if not chapter_text:
            print(f"错误：未找到第 {args.chapter} 章的文件")
            sys.exit(1)
        
        # 加载规划文档
        layers = load_layer_files()
        # 加载上一章内容（如果有）
        prev_chapter_tail = load_chapter(args.chapter - 1)[-500:] if args.chapter > 1 else ""
        # 加载本章大纲（需根据实际大纲格式调整，此处为示例）
        chapter_outline = "未找到大纲条目"  # 需补充实际逻辑
        
        # 构建章节评估提示词
        prompt = CHAPTER_PROMPT.format(
            voice=layers["voice"],
            world=layers["world"],
            characters=layers["characters"],
            canon=layers["canon"],
            chapter_outline=chapter_outline,
            prev_chapter_tail=prev_chapter_tail,
            chapter_text=chapter_text
        )
        
        # 调用评估模型并解析结果
        raw = call_judge(prompt)
        result = parse_json_response(raw)
        
        # 添加机械检查分数
        result["slop_check"] = slop_score(chapter_text)
        
        # 保存评估结果
        log_path = EVAL_LOG_DIR / f"chapter_{args.chapter:02d}_eval_{eval_time}.json"
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"第 {args.chapter} 章评估完成，结果已保存至: {log_path}")
        
    elif args.full:
        print("开始评估完整小说...")
        # 此处需补充完整小说评估的逻辑
        chapters = load_all_chapters()
        if not chapters:
            print("错误：未找到任何章节文件")
            sys.exit(1)
        
        # 示例：汇总所有章节评估（需补充实际逻辑）
        full_results = {
            "chapters_count": len(chapters),
            "eval_time": eval_time,
            "chapter_evals": {}
        }
        
        for chap_num, chap_text in chapters.items():
            print(f"正在评估第 {chap_num} 章...")
            # 此处复用章节评估逻辑
            layers = load_layer_files()
            prev_chapter_tail = chapters[chap_num - 1][-500:] if chap_num > 1 else ""
            chapter_outline = "未找到大纲条目"
            
            prompt = CHAPTER_PROMPT.format(
                voice=layers["voice"],
                world=layers["world"],
                characters=layers["characters"],
                canon=layers["canon"],
                chapter_outline=chapter_outline,
                prev_chapter_tail=prev_chapter_tail,
                chapter_text=chap_text
            )
            
            raw = call_judge(prompt)
            chap_result = parse_json_response(raw)
            chap_result["slop_check"] = slop_score(chap_text)
            full_results["chapter_evals"][chap_num] = chap_result
        
        # 保存完整评估结果
        log_path = EVAL_LOG_DIR / f"full_novel_eval_{eval_time}.json"
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(full_results, f, ensure_ascii=False, indent=2)
        print(f"完整小说评估完成，结果已保存至: {log_path}")
        
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()