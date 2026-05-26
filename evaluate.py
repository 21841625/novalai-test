#!/usr/bin/env python3
"""
评估脚本 - 平衡模式版本
双维度评估：同时检查追读适配和内容质感，拒绝模板化口水文
"""
import os
import sys
import json
import re
import argparse
from pathlib import Path
from datetime import datetime
from api_client import call_llm, get_judge_model, get_api_key, get_api_provider

BASE_DIR = Path(__file____)
JUDGE_MODEL = get_judge_model()
API_KEY = get_api_key()
API_PROVIDER = get_api_provider()
# 模式配置，统一和其他脚本一致
NOVEL_MODE = os.environ.get("AUTONOVEL_MODE", "balance").lower()

CHAPTERS_DIR = BASE_DIR / "out_doc" / "chapters"
EVAL_LOG_DIR = BASE_DIR / "eval_logs"
EVAL_LOG_DIR.mkdir(exist_ok=True)

# 基础评估提示，根据模式切换
def get_foundation_prompt(layers):
    voice = layers["voice"]
    world = layers["world"]
    characters = layers["characters"]
    outline = layers["outline"]
    
    if NOVEL_MODE == "shuangwen":
        return f"""Evaluate the quality of these planning documents for a Chinese web novel.
VOICE DOC: {voice}
WORLD BIBLE: {world}
CHARACTERS: {characters}
OUTLINE: {outline}
Evaluate each document on these criteria:
1. VOICE: Is the voice specific and actionable? Does it give concrete guidance?
2. WORLD: Is the world detailed enough to write against? Does it have rules and constraints?
3. CHARACTERS: Are characters distinct? Do they have wants and flaws that will create conflict?
4. OUTLINE: Does it have clear golden first 3 chapters? Does every chapter have a hook?
Score each dimension 0-10. Provide specific feedback for improvement.
Respond with JSON: {{
  "voice": {{"score": N, "weakest": "specific flaw", "fix": "actionable suggestion", "note": "..."}},
  "world": {{"score": N, "weakest": "...", "fix": "...", "note": "..."}},
  "characters": {{"score": N, "weakest": "...", "fix": "...", "note": "..."}},
  "outline": {{"score": N, "weakest": "...", "fix": "...", "note": "..."}},
  "overall_score": N,
  "top_3_gaps": ["gap 1", "gap 2", "gap 3"],
  "ready_to_write": true/false
}}
"""
    elif NOVEL_MODE == "literature":
        return f"""Evaluate the quality of these planning documents for a fantasy novel.
VOICE DOC: {voice}
WORLD BIBLE: {world}
CHARACTERS: {characters}
OUTLINE: {outline}
Evaluate each document on these criteria:
1. VOICE: Is the voice specific and actionable? Does it give concrete guidance?
2. WORLD: Is the world detailed enough to write against? Does it have rules and constraints?
3. CHARACTERS: Are characters distinct? Do they have wants and flaws that will create conflict?
4. OUTLINE: Does it have a clear three-act structure? Are character arcs visible?
Score each dimension 0-10. Provide specific feedback for improvement.
Respond with JSON: {{
  "voice": {{"score": N, "weakest": "specific flaw", "fix": "actionable suggestion", "note": "..."}},
  "world": {{"score": N, "weakest": "...", "fix": "...", "note": "..."}},
  "characters": {{"score": N, "weakest": "...", "fix": "...", "note": "..."}},
  "outline": {{"score": N, "weakest": "...", "fix": "...", "note": "..."}},
  "overall_score": N,
  "top_3_gaps": ["gap 1", "gap 2", "gap 3"],
  "ready_to_write": true/false
}}
"""
    else: # balance 平衡模式
        return f"""Evaluate the quality of these planning documents for a high-quality Chinese web novel.
VOICE DOC: {voice}
WORLD BIBLE: {world}
CHARACTERS: {characters}
OUTLINE: {outline}
双维度评估：
1. 追读适配：节奏紧凑度、开篇抓眼度、钩子有效性（确保读者能追下去）
2. 内容质感：创意新意、人物立体度、世界观深度、文笔质感（确保不是口水文）
额外检测：有没有烂大街的俗套设定？比如反派降智/主角开挂/穿越重生模板？
Evaluate each document on these criteria:
1. VOICE: Is the voice specific and actionable? Does it give concrete guidance?
2. WORLD: Is the world detailed enough? Does it have unique original settings, not cliche templates?
3. CHARACTERS: Are characters distinct? Do they have wants and flaws that will create conflict?
4. OUTLINE: Does it have a clear opening hook in first 3 chapters? Does every chapter have a natural hook?
Score each dimension 0-10. Provide specific feedback for improvement.
Respond with JSON: {{
  "voice": {{"score": N, "weakest": "specific flaw", "fix": "actionable suggestion", "note": "..."}},
  "world": {{"score": N, "weakest": "...", "fix": "...", "note": "...", "is_cliche": false/true}},
  "characters": {{"score": N, "weakest": "...", "fix": "...", "note": "..."}},
  "outline": {{"score": N, "weakest": "...", "fix": "...", "note": "..."}},
  "overall_score": N,
  "top_3_gaps": ["gap 1", "gap 2", "gap 3"],
  "cliche_warnings": ["any cliche found, if any"],
  "ready_to_write": true/false
}}
"""

def call_judge(prompt, max_tokens=8000):
    """Call the judge model."""
    return call_llm(prompt, JUDGE_MODEL, max_tokens, temperature=0.2)

def parse_json_response(raw):
    """Extract JSON from potentially messy response."""
    try:
        # Try to find JSON block
        json_start = raw.find("{")
        json_end = raw.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            return json.loads(raw[json_start:json_end])
    except:
        pass
    return {"raw": raw[:500]}

def slop_score(text):
    """
    机械检测：AI烂文检测，加了内容密度检测，避免水字数
    """
    slop_penalty = 0.0
    
    # 原来的检测，全部保留
    words = text.lower().split()
    repeated = sum(1 for i in range(len(words)-2) if words[i] == words[i+1])
    if repeated > 3:
        slop_penalty += 0.5
    
    passive_count = len(re.findall(r'\b(was|were|been)\b.*?\b(ed\b|\bby\b)', text))
    if passive_count > 10:
        slop_penalty += 0.3
    
    if text.count("a sense of") > 3:
        slop_penalty += 0.2
    
    vague_count = sum(text.count(w) for w in ["very", "quite", "rather", "somewhat"])
    if vague_count > 15:
        slop_penalty += 0.3
    
    sentences = re.split(r'[.!?]+', text)
    lens = [len(s.split()) for s in sentences if len(s) > 10]
    if len(lens) > 20:
        avg_len = sum(lens) / len(lens)
        if all(abs(len(s.split()) - avg_len) < 5 for s in sentences if len(s) > 10):
            slop_penalty += 0.4
    
    # 新增：内容密度检测，避免水字数
    word_count = len(text.split())
    if word_count > 500:
        info_points = len(re.findall(r'[。！？，]', text)) # 简单的信息点统计，可优化
        density = info_points / word_count * 1000
        if density < 5: # 信息密度太低，就是水字数
            slop_penalty += 1.0
            logger.info(f"检测到水字数，信息密度过低: {density}")
    
    return {
        "slop_penalty": round(slop_penalty, 2),
        "repeated_words": repeated,
        "passive_instances": passive_count,
        "sense_of_count": text.count("a sense of"),
        "vague_modifiers": vague_count,
        "info_density": round(density, 2) if word_count >500 else 0
    }

def load_layer_files():
    """Load all planning documents."""
    layers = {}
    md_dir = BASE_DIR / "out_doc" / "md_file"
    for name in ["voice", "world", "characters", "outline", "canon"]:
        path = md_dir / f"{name}.md"
        layers[name] = path.read_text() if path.exists() else "(not found)"
    return layers

def load_chapter(num):
    """Load a single chapter."""
    path = CHAPTERS_DIR / f"第{num}章_*.md"
    files = list(CHAPTERS_DIR.glob(f"第{num}章_*.md"))
    if files:
        return files[0].read_text()
    # 兼容原来的英文文件名
    path = CHAPTERS_DIR / f"ch_{num:02d}.md"
    return path.read_text() if path.exists() else ""

def load_all_chapters():
    """Load all chapters as a dict {num: text}."""
    chapters = {}
    # 兼容中文和英文文件名
    for path in sorted(CHAPTERS_DIR.glob("第*章_*.md")):
        match = re.match(r'第(\d+)章_', path.name)
        if match:
            chapters[int(match.group(1))] = path.read_text()
    for path in sorted(CHAPTERS_DIR.glob("ch_*.md")):
        match = re.match(r'ch_(\d+)\.md', path.name)
        if match:
            chapters[int(match.group(1))] = path.read_text()
    return chapters

def evaluate_foundation():
    """Evaluate planning documents."""
    layers = load_layer_files()
    prompt = get_foundation_prompt(layers)
    raw = call_judge(prompt)
    result = parse_json_response(raw)
    return result

# --- Chapter Evaluation ---
def get_chapter_prompt(layers, chapter_outline, prev_chapter_tail, chapter_text):
    voice = layers["voice"]
    world = layers["world"]
    characters = layers["characters"]
    canon = layers["canon"]
    
    if NOVEL_MODE == "shuangwen":
        return f"""Evaluate this chapter against the planning documents.
VOICE DEFINITION (Part 2 is the prose style): {voice}
WORLD BIBLE: {world}
CHARACTER REGISTRY: {characters}
CANON (hard facts): {canon}
THIS CHAPTER'S OUTLINE ENTRY: {chapter_outline}
PREVIOUS CHAPTER'S ENDING: {prev_chapter_tail}
CHAPTER TEXT: {chapter_text}
Evaluate these dimensions:
1. VOICE ADHERENCE: How well does the prose match the voice definition?
2. BEAT COVERAGE: Did it hit every beat from the outline?
3. CHARACTER VOICE: Is dialogue distinct? Do characters sound like individuals?
4. PLANTS SEEDED: Were foreshadowing elements placed naturally?
5. PROSE QUALITY: Sentence variety, specificity, metaphors.
6. CONTINUITY: Does it follow logically from the previous chapter?
7. CANON COMPLIANCE: Check all facts against canon.
8. LORE INTEGRATION: Does the world do work in this chapter?
9. HOOK EFFECTIVENESS: Is the ending hook strong enough to make readers chase?
10. SHUANG POINT: Is there a natural shuang point in this chapter?
SCORING GUIDELINES (0-10 scale):
- 0-3: Major problems, needs complete rewrite
- 4-5: Significant flaws, needs heavy revision
- 6: Median AI chapter - competent but unremarkable
- 7: Good - solid execution with minor issues
- 8: Very good - few weaknesses, some standout moments
- 9: Excellent - exceptional craft throughout
- 10: Perfection (does not exist for first drafts)
Respond with JSON: {{
  "voice_adherence": {{"score": N, "weakest_moment": "...", "fix": "...", "note": "..."}},
  "beat_coverage": {{"score": N, "weakest_moment": "...", "fix": "...", "note": "..."}},
  "character_voice": {{"score": N, "weakest_moment": "...", "fix": "...", "note": "..."}},
  "plants_seeded": {{"score": N, "weakest_moment": "...", "fix": "...", "note": "..."}},
  "prose_quality": {{"score": N, "weakest_sentence": "...", "fix": "...", "strongest_sentence": "...", "note": "..."}},
  "continuity": {{"score": N, "note": "..."}},
  "canon_compliance": {{"score": N, "violations": ["list any found"], "note": "..."}},
  "lore_integration": {{"score": N, "weakest_moment": "...", "fix": "...", "note": "..."}},
  "hook_effectiveness": {{"score": N, "weakest_moment": "...", "fix": "...", "note": "..."}},
  "shuang_point": {{"score": N, "note": "..."}},
  "three_weakest_sentences": ["quote 1", "quote 2", "quote 3"],
  "three_strongest_sentences": ["quote 1", "quote 2", "quote 3"],
  "ai_patterns_detected": ["list any AI writing patterns found"],
  "overall_score": N,
  "weakest_dimension": "...",
  "top_3_revisions": ["specific, actionable revision 1", "revision 2", "revision 3"],
  "new_canon_entries": ["any new facts established in this chapter"]
}}
FINAL CHECK: If your overall_score is above 7, re-read your weakest_moment quotes. If any of them describe a problem that an editor would flag, your score is too high.
"""
    elif NOVEL_MODE == "literature":
        return f"""Evaluate this chapter against the planning documents.
VOICE DEFINITION (Part 2 is the prose style): {voice}
WORLD BIBLE: {world}
CHARACTER REGISTRY: {characters}
CANON (hard facts): {canon}
THIS CHAPTER'S OUTLINE ENTRY: {chapter_outline}
PREVIOUS CHAPTER'S ENDING: {prev_chapter_tail}
CHAPTER TEXT: {chapter_text}
Evaluate these 9 dimensions:
1. VOICE ADHERENCE: How well does the prose match the voice definition?
2. BEAT COVERAGE: Did it hit every beat from the outline?
3. CHARACTER VOICE: Is dialogue distinct? Do characters sound like individuals?
4. PLANTS SEEDED: Were foreshadowing elements placed naturally?
5. PROSE QUALITY: Sentence variety, specificity, metaphors.
6. CONTINUITY: Does it follow logically from the previous chapter?
7. CANON COMPLIANCE: Check all facts against canon.
8. LORE INTEGRATION: Does the world do work in this chapter?
9. ENGAGEMENT: Would a reader turn the page? Is there surprise?
SCORING GUIDELINES (0-10 scale):
- 0-3: Major problems, needs complete rewrite
- 4-5: Significant flaws, needs heavy revision
- 6: Median AI chapter - competent but unremarkable
- 7: Good - solid execution with minor issues
- 8: Very good - few weaknesses, some standout moments
- 9: Excellent - exceptional craft throughout
- 10: Perfection (does not exist for first drafts)
Respond with JSON: {{
  "voice_adherence": {{"score": N, "weakest_moment": "...", "fix": "...", "note": "..."}},
  "beat_coverage": {{"score": N, "weakest_moment": "...", "fix": "...", "note": "..."}},
  "character_voice": {{"score": N, "weakest_moment": "...", "fix": "...", "note": "..."}},
  "plants_seeded": {{"score": N, "weakest_moment": "...", "fix": "...", "note": "..."}},
  "prose_quality": {{"score": N, "weakest_sentence": "...", "fix": "...", "strongest_sentence": "...", "note": "..."}},
  "continuity": {{"score": N, "note": "..."}},
  "canon_compliance": {{"score": N, "violations": ["list any found"], "note": "..."}},
  "lore_integration": {{"score": N, "weakest_moment": "...", "fix": "...", "note": "..."}},
  "engagement": {{"score": N, "weakest_moment": "...", "fix": "...", "note": "..."}},
  "three_weakest_sentences": ["quote 1", "quote 2", "quote 3"],
  "three_strongest_sentences": ["quote 1", "quote 2", "quote 3"],
  "ai_patterns_detected": ["list any AI writing patterns found"],
  "overall_score": N,
  "weakest_dimension": "...",
  "top_3_revisions": ["specific, actionable revision 1", "revision 2", "revision 3"],
  "new_canon_entries": ["any new facts established in this chapter"]
}}
FINAL CHECK: If your overall_score is above 7, re-read your weakest_moment quotes. If any of them describe a problem that an editor would flag, your score is too high.
"""
    else: # balance 平衡模式
        return f"""Evaluate this chapter against the planning documents.
VOICE DEFINITION (Part 2 is the prose style): {voice}
WORLD BIBLE: {world}
CHARACTER REGISTRY: {characters}
CANON (hard facts): {canon}
THIS CHAPTER'S OUTLINE ENTRY: {chapter_outline}
PREVIOUS CHAPTER'S ENDING: {prev_chapter_tail}
CHAPTER TEXT: {chapter_text}
双维度评估：
1. 追读适配：节奏紧凑度、钩子有效性、开篇抓眼度（确保读者能追下去）
2. 内容质感：创意新意、人物立体度、世界观深度、文笔质感（确保不是口水文）
额外检测：有没有烂大街的俗套内容？比如反派降智/主角开挂/重复的打脸剧情？有没有水字数？
Evaluate these dimensions:
1. VOICE ADHERENCE: How well does the prose match the voice definition?
2. BEAT COVERAGE: Did it hit every beat from the outline?
3. CHARACTER VOICE: Is dialogue distinct? Do characters sound like individuals?
4. PLANTS SEEDED: Were foreshadowing elements placed naturally?
5. PROSE QUALITY: Sentence variety, specificity, metaphors, no cliche expressions.
6. CONTINUITY: Does it follow logically from the previous chapter?
7. CANON COMPLIANCE: Check all facts against canon.
8. LORE INTEGRATION: Does the world do work in this chapter, not just set dressing?
9. HOOK EFFECTIVENESS: Is the ending hook natural and strong enough to make readers chase?
10. ORIGINALITY: Is this content original, not cliche template?
SCORING GUIDELINES (0-10 scale):
- 0-3: Major problems, needs complete rewrite
- 4-5: Significant flaws, needs heavy revision
- 6: Median AI chapter - competent but unremarkable
- 7: Good - solid execution with minor issues
- 8: Very good - few weaknesses, some standout moments
- 9: Excellent - exceptional craft throughout
- 10: Perfection (does not exist for first drafts)
Respond with JSON: {{
  "voice_adherence": {{"score": N, "weakest_moment": "...", "fix": "...", "note": "..."}},
  "beat_coverage": {{"score": N, "weakest_moment": "...", "fix": "...", "note": "..."}},
  "character_voice": {{"score": N, "weakest_moment": "...", "fix": "...", "note": "..."}},
  "plants_seeded": {{"score": N, "weakest_moment": "...", "fix": "...", "note": "..."}},
  "prose_quality": {{"score": N, "weakest_sentence": "...", "fix": "...", "strongest_sentence": "...", "note": "..."}},
  "continuity": {{"score": N, "note": "..."}},
  "canon_compliance": {{"score": N, "violations": ["list any found"], "note": "..."}},
  "lore_integration": {{"score": N, "weakest_moment": "...", "fix": "...", "note": "..."}},
  "hook_effectiveness": {{"score": N, "weakest_moment": "...", "fix": "...", "note": "..."}},
  "originality": {{"score": N, "cliche_warnings": ["any cliche found, if any"], "note": "..."}},
  "three_weakest_sentences": ["quote 1", "quote 2", "quote 3"],
  "three_strongest_sentences": ["quote 1", "quote 2", "quote 3"],
  "ai_patterns_detected": ["list any AI writing patterns found"],
  "overall_score": N,
  "weakest_dimension": "...",
  "top_3_revisions": ["specific, actionable revision 1", "revision 2", "revision 3"],
  "new_canon_entries": ["any new facts established in this chapter"]
}}
FINAL CHECK: If your overall_score is above 7, re-read your weakest_moment quotes. If any of them describe a problem that an editor would flag, your score is too high.
"""

def evaluate_chapter(chapter_num):
    layers = load_layer_files()
    chapter_text = load_chapter(chapter_num)
    if not chapter_text.strip():
        return {"error": f"Chapter {chapter_num} is empty or missing", "overall_score": 0.0}
    
    # 提取章节大纲
    outline = layers["outline"]
    ch_pattern = rf'###\s*第{chapter_num}章.*?(?=###\s*第\d|## Act|## Foreshadowing|$)'
    ch_match = re.search(ch_pattern, outline, re.DOTALL)
    if not ch_match:
        ch_pattern = rf'###\s*Ch\s*{chapter_num}\b.*?(?=###\s*Ch\s*\d|## Act|## Foreshadowing|$)'
        ch_match = re.search(ch_pattern, outline, re.DOTALL)
    chapter_outline = ch_match.group(0) if ch_match else "(outline entry not found)"
    
    # 加载上一章结尾
    prev_text = load_chapter(chapter_num - 1) if chapter_num > 1 else "(first chapter)"
    prev_tail = prev_text[-3000:] if len(prev_text) > 3000 else prev_text
    
    prompt = get_chapter_prompt(layers, chapter_outline, prev_tail, chapter_text)
    raw = call_judge(prompt, max_tokens=8000)
    result = parse_json_response(raw)
    
    # 机械烂文检测，加了内容密度
    slop = slop_score(chapter_text)
    result["slop"] = slop
    if "overall_score" in result:
        adjusted = max(0, result["overall_score"] - slop["slop_penalty"])
        result["raw_judge_score"] = result["overall_score"]
        result["overall_score"] = round(adjusted, 2)
    
    return result

# --- Full Novel Evaluation ---
def get_full_prompt(layers, chapter_summaries):
    voice = layers["voice"]
    world_summary = layers["world"][:3000]
    characters = layers["characters"]
    outline = layers["outline"]
    
    if NOVEL_MODE == "shuangwen":
        return f"""Evaluate this complete web novel holistically.
VOICE DEFINITION: {voice}
WORLD BIBLE: {world_summary}
CHARACTER REGISTRY: {characters}
OUTLINE + FORESHADOWING LEDGER: {outline}
CHAPTER SUMMARIES AND SCORES: {chapter_summaries}
Score these novel-level dimensions 0-10:
- arc_completion: Do character arcs resolve satisfyingly?
- pacing_curve: Is the pacing fast enough, with enough shuang points?
- theme_coherence: Are themes explored consistently?
- foreshadowing_resolution: Are all planted threads harvested?
- world_consistency: Any lore contradictions across chapters?
- voice_consistency: Is the voice steady throughout?
- overall_engagement: Is this a compelling read start to finish?
Respond with JSON: {{
  "arc_completion": {{"score": N, "note": "..."}},
  "pacing_curve": {{"score": N, "note": "..."}},
  "theme_coherence": {{"score": N, "note": "..."}},
  "foreshadowing_resolution": {{"score": N, "note": "..."}},
  "world_consistency": {{"score": N, "note": "..."}},
  "voice_consistency": {{"score": N, "note": "..."}},
  "overall_engagement": {{"score": N, "note": "..."}},
  "novel_score": N,
  "weakest_dimension": "...",
  "weakest_chapter": N,
  "top_suggestion": "..."
}}
"""
    elif NOVEL_MODE == "literature":
        return f"""Evaluate this complete novel holistically.
VOICE DEFINITION: {voice}
WORLD BIBLE: {world_summary}
CHARACTER REGISTRY: {characters}
OUTLINE + FORESHADOWING LEDGER: {outline}
CHAPTER SUMMARIES AND SCORES: {chapter_summaries}
Score these novel-level dimensions 0-10:
- arc_completion: Do character arcs resolve satisfyingly?
- pacing_curve: Does tension build properly across the book?
- theme_coherence: Are themes explored consistently?
- foreshadowing_resolution: Are all planted threads harvested?
- world_consistency: Any lore contradictions across chapters?
- voice_consistency: Is the voice steady throughout?
- overall_engagement: Is this a compelling read start to finish?
Respond with JSON: {{
  "arc_completion": {{"score": N, "note": "..."}},
  "pacing_curve": {{"score": N, "note": "..."}},
  "theme_coherence": {{"score": N, "note": "..."}},
  "foreshadowing_resolution": {{"score": N, "note": "..."}},
  "world_consistency": {{"score": N, "note": "..."}},
  "voice_consistency": {{"score": N, "note": "..."}},
  "overall_engagement": {{"score": N, "note": "..."}},
  "novel_score": N,
  "weakest_dimension": "...",
  "weakest_chapter": N,
  "top_suggestion": "..."
}}
"""
    else: # balance
        return f"""Evaluate this complete high-quality web novel holistically.
VOICE DEFINITION: {voice}
WORLD BIBLE: {world_summary}
CHARACTER REGISTRY: {characters}
OUTLINE + FORESHADOWING LEDGER: {outline}
CHAPTER SUMMARIES AND SCORES: {chapter_summaries}
双维度评估：
1. 追读适配：整体节奏、钩子的连贯性，能不能让读者一直追下去
2. 内容质感：整体的创意、人物、世界观，有没有深度，能不能让人回味
额外检测：有没有俗套的重复剧情？有没有水字数？
Score these novel-level dimensions 0-10:
- arc_completion: Do character arcs resolve satisfyingly?
- pacing_curve: Is the pacing steady, with natural hooks, no slow parts?
- theme_coherence: Are themes explored consistently?
- foreshadowing_resolution: Are all planted threads harvested?
- world_consistency: Any lore contradictions across chapters?
- voice_consistency: Is the voice steady throughout?
- originality: Is the whole novel original, not cliche template?
- overall_engagement: Is this a compelling read start to finish, can readers回味 after reading?
Respond with JSON: {{
  "arc_completion": {{"score": N, "note": "..."}},
  "pacing_curve": {{"score": N, "note": "..."}},
  "theme_coherence": {{"score": N, "note": "..."}},
  "foreshadowing_resolution": {{"score": N, "note": "..."}},
  "world_consistency": {{"score": N, "note": "..."}},
  "voice_consistency": {{"score": N, "note": "..."}},
  "originality": {{"score": N, "cliche_warnings": ["any cliche found, if any"], "note": "..."}},
  "overall_engagement": {{"score": N, "note": "..."}},
  "novel_score": N,
  "weakest_dimension": "...",
  "weakest_chapter": N,
  "top_suggestion": "..."
}}
"""

def evaluate_full():
    layers = load_layer_files()
    chapters = load_all_chapters()
    if not chapters:
        return {"error": "No chapters found", "novel_score": 0.0}
    
    # 构建章节摘要
    summaries = []
    for num in sorted(chapters.keys()):
        text = chapters[num]
        word_count = len(text.split())
        head = text[:500]
        tail = text[-500:] if len(text) > 500 else ""
        summaries.append(
            f"第{num}章 ({word_count} words):\n"
            f" Opening: {head}...\n"
            f" Closing: ...{tail}\n"
        )
    
    prompt = get_full_prompt(layers, "\n".join(summaries))
    raw = call_judge(prompt)
    return parse_json_response(raw)

# --- Main ---
def main():
    parser = argparse.ArgumentParser(description="Evaluate the novel")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--phase", choices=["foundation"], help="Evaluate planning documents")
    group.add_argument("--chapter", type=int, help="Evaluate a specific chapter number")
    group.add_argument("--full", action="store_true", help="Evaluate the entire novel")
    args = parser.parse_args()

    if not API_KEY:
        print(f"ERROR: Set {'DEEPSEEK_API_KEY' if API_PROVIDER == 'deepseek' else 'ANTHROPIC_API_KEY'} in .env first", file=sys.stderr)
        sys.exit(1)

    if args.phase == "foundation":
        result = evaluate_foundation()
        score_key = "overall_score"
    elif args.chapter is not None:
        result = evaluate_chapter(args.chapter)
        score_key = "overall_score"
    elif args.full:
        result = evaluate_full()
        score_key = "novel_score"

    # 打印结果，完全保留你原来的逻辑
    print("---")
    if score_key in result:
        print(f"{score_key}: {result[score_key]}")
        for key, val in result.items():
            if key == score_key:
                continue
            if isinstance(val, dict):
                print(f"{key}: {val.get('score', 'N/A')} -- {val.get('note', '')}")
            else:
                print(f"{key}: {val}")
    
    # 保存日志
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode = args.phase or (f"ch{args.chapter:02d}" if args.chapter else "full")
    log_path = EVAL_LOG_DIR / f"{timestamp}_{mode}_{NOVEL_MODE}.json"
    with open(log_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\neval_log: {log_path}")

if __name__ == "__main__":
    main()