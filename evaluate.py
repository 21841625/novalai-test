#!/usr/bin/env python3
"""
Evaluate the novel or its components using the judge model.

Usage:
  python evaluate.py --phase foundation    # Evaluate planning docs
  python evaluate.py --chapter 1          # Evaluate chapter 1
  python evaluate.py --full               # Evaluate full novel
"""
import os
import sys
import json
import re
import argparse
from pathlib import Path
from datetime import datetime

from api_client import call_llm, get_judge_model, get_api_key, get_api_provider

BASE_DIR = Path(__file__).parent

JUDGE_MODEL = get_judge_model()
API_KEY = get_api_key()
API_PROVIDER = get_api_provider()

CHAPTERS_DIR = BASE_DIR / "chapters"
EVAL_LOG_DIR = BASE_DIR / "eval_logs"
EVAL_LOG_DIR.mkdir(exist_ok=True)

FOUNDATION_PROMPT = """Evaluate the quality of these planning documents for a fantasy novel.

VOICE DOC:
{voice}

WORLD BIBLE:
{world}

CHARACTERS:
{characters}

OUTLINE:
{outline}

Evaluate each document on these criteria:
1. VOICE: Is the voice specific and actionable? Does it give concrete guidance?
   Is there a clear "no" list (banned words/patterns)? Is the tone distinct?
   
2. WORLD: Is the world detailed enough to write against? Does it have rules
   and constraints? Is there enough texture for sensory description?
   Are the key locations and their significance clear?

3. CHARACTERS: Are characters distinct? Do they have specific speech patterns?
   Do they have wants and flaws that will create conflict? Is the protagonist
   compelling?

4. OUTLINE: Does it have a clear three-act structure? Are character arcs
   visible? Does it plant foreshadowing? Are chapters sized appropriately?

Score each dimension 0-10. Provide specific feedback for improvement.

Respond with JSON:
{{
  "voice": {{"score": N, "weakest": "specific flaw", "fix": "actionable suggestion", "note": "..."}},
  "world": {{"score": N, "weakest": "...", "fix": "...", "note": "..."}},
  "characters": {{"score": N, "weakest": "...", "fix": "...", "note": "..."}},
  "outline": {{"score": N, "weakest": "...", "fix": "...", "note": "..."}},
  "overall_score": N,
  "top_3_gaps": ["gap 1", "gap 2", "gap 3"],
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
    """Mechanical checks for AI writing patterns."""
    slop_penalty = 0.0
    
    # Check for repeated words/phrases
    words = text.lower().split()
    repeated = sum(1 for i in range(len(words)-2) if words[i] == words[i+1])
    if repeated > 3:
        slop_penalty += 0.5
    
    # Check for passive voice patterns
    passive_count = len(re.findall(r'\b(was|were|been)\b.*?\b(ed\b|\bby\b)', text))
    if passive_count > 10:
        slop_penalty += 0.3
    
    # Check for "sense of" pattern
    if text.count("a sense of") > 3:
        slop_penalty += 0.2
    
    # Check for vague modifiers
    vague_count = sum(text.count(w) for w in ["very", "quite", "rather", "somewhat"])
    if vague_count > 15:
        slop_penalty += 0.3
    
    # Check for sentence length uniformity
    sentences = re.split(r'[.!?]+', text)
    lens = [len(s.split()) for s in sentences if len(s) > 10]
    if len(lens) > 20:
        avg_len = sum(lens) / len(lens)
        if all(abs(len(s.split()) - avg_len) < 5 for s in sentences if len(s) > 10):
            slop_penalty += 0.4
    
    return {
        "slop_penalty": round(slop_penalty, 2),
        "repeated_words": repeated,
        "passive_instances": passive_count,
        "sense_of_count": text.count("a sense of"),
        "vague_modifiers": vague_count
    }


def load_layer_files():
    """Load all planning documents."""
    layers = {}
    for name in ["voice", "world", "characters", "outline", "canon"]:
        path = BASE_DIR / f"{name}.md"
        layers[name] = path.read_text() if path.exists() else "(not found)"
    return layers


def load_chapter(num):
    """Load a single chapter."""
    path = CHAPTERS_DIR / f"ch_{num:02d}.md"
    return path.read_text() if path.exists() else ""


def load_all_chapters():
    """Load all chapters as a dict {num: text}."""
    chapters = {}
    for path in sorted(CHAPTERS_DIR.glob("ch_*.md")):
        match = re.match(r'ch_(\d+)\.md', path.name)
        if match:
            chapters[int(match.group(1))] = path.read_text()
    return chapters


def evaluate_foundation():
    """Evaluate planning documents."""
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


# --- Chapter Evaluation ---

CHAPTER_PROMPT = """Evaluate this chapter against the planning documents.

VOICE DEFINITION (Part 2 is the prose style):
{voice}

WORLD BIBLE:
{world}

CHARACTER REGISTRY:
{characters}

CANON (hard facts):
{canon}

THIS CHAPTER'S OUTLINE ENTRY:
{chapter_outline}

PREVIOUS CHAPTER'S ENDING:
{prev_chapter_tail}

CHAPTER TEXT:
{chapter_text}

Evaluate these 9 dimensions:

1. VOICE ADHERENCE: How well does the prose match the voice definition?
   Check sentence variation, vocabulary, body-before-emotion, tone.

2. BEAT COVERAGE: Did it hit every beat from the outline? Were beats
   dramatized (shown through scene) or merely mentioned (told)?

3. CHARACTER VOICE: Is dialogue distinct? Do characters sound like
   individuals? Does Cass sound like a specific 14-year-old?

4. PLANTS SEEDED: Were foreshadowing elements placed naturally? Not too
   obvious, not invisible.

5. PROSE QUALITY: Sentence variety, specificity, metaphors from character's
   experience, show-don't-tell at emotional peaks.

6. CONTINUITY: Does it follow logically from the previous chapter? Emotional
   continuity as well as plot.

7. CANON COMPLIANCE: Check all facts against canon. List violations.

8. LORE INTEGRATION: Does the world do work in this chapter, or is it
   just set dressing?

9. ENGAGEMENT: Would a reader turn the page? Is there surprise?
   Predictable excellence is still predictable.

SCORING GUIDELINES (0-10 scale):
- 0-3: Major problems, needs complete rewrite
- 4-5: Significant flaws, needs heavy revision
- 6: Median AI chapter - competent but unremarkable
- 7: Good - solid execution with minor issues
- 8: Very good - few weaknesses, some standout moments
- 9: Excellent - exceptional craft throughout
- 10: Perfection (does not exist for first drafts)

DIMENSION-SPECIFIC QUESTIONS:

1. VOICE ADHERENCE: Does the prose match voice.md Part 2? Check: sentence
   rhythm variation, vocabulary wells, body-before-emotion principle,
   the specific tone described. Quote the strongest voice moment AND
   the weakest. Does ANY passage sound like generic fantasy prose that
   could appear in any novel? If yes, score 7 max.

2. BEAT COVERAGE: Did it hit every beat from the outline? Were beats
   dramatized or merely mentioned? A beat that's summarized in a sentence
   instead of lived in a scene counts as half-hit. Score reflects
   QUALITY of beat execution, not just presence.

3. CHARACTER VOICE: Remove all dialogue tags mentally. Can you tell who's
   speaking? Do characters ever sound alike? Does dialogue read as speech
   or as written prose? Does Cass sound like a specific 14-year-old, or
   like "young protagonist"? Does anyone say something surprising -- not
   just the right thing, but a REAL thing? Characters who never stumble,
   hesitate, or say something slightly wrong are AI-pattern characters.

4. PLANTS SEEDED: Were foreshadowing elements placed naturally? A plant
   that's obvious is worse than a plant that's invisible. Score based on
   HOW WELL they're integrated, not just whether they're present.

5. PROSE QUALITY: Sentence variety (measure: do 3+ consecutive sentences
   start the same way?). Specificity (concrete nouns > abstract).
   Metaphors from Cass's experience, not from a thesaurus. Show-don't-tell
   at emotional peaks. QUOTE the weakest sentence and explain why. Also
   check for: repeated phrases, leaned-on constructions, paragraphs that
   could be cut without loss.

6. CONTINUITY: Does it follow logically from the previous chapter? Emotional
   continuity as well as plot continuity. Does the character's state of
   mind track?

7. CANON COMPLIANCE: Check ALL facts against canon. List violations.
   One major violation caps score at 6. Check: character names, locations,
   magic system rules, timeline, established events, physical descriptions.

8. LORE INTEGRATION: Does the world do WORK in this chapter, or is it
   set dressing? A scene that could happen in any fantasy city with
   find-and-replace on proper nouns scores 5 max.

9. ENGAGEMENT: Would a reader turn the page? Where does tension come from --
   plot, character, mystery, prose? Is there a moment that SURPRISES?
   Predictable excellence is still predictable. Score 8+ only if the
   chapter does something unexpected.

Respond with JSON:
{{
  "voice_adherence": {{"score": N, "weakest_moment": "quote the specific weak passage", "fix": "how to improve it", "note": "..."}},
  "beat_coverage": {{"score": N, "weakest_moment": "...", "fix": "...", "note": "..."}},
  "character_voice": {{"score": N, "weakest_moment": "...", "fix": "...", "note": "..."}},
  "plants_seeded": {{"score": N, "weakest_moment": "...", "fix": "...", "note": "..."}},
  "prose_quality": {{"score": N, "weakest_sentence": "quote it", "fix": "rewrite suggestion", "strongest_sentence": "quote it", "note": "..."}},
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

FINAL CHECK: If your overall_score is above 7, re-read your weakest_moment
quotes. If any of them describe a problem that an editor would flag, your
score is too high. The median AI chapter is a 6. An 8 is exceptional. A 9
is rare. A 10 does not exist for a first draft.
"""


def evaluate_chapter(chapter_num):
    layers = load_layer_files()
    chapter_text = load_chapter(chapter_num)
    if not chapter_text.strip():
        return {"error": f"Chapter {chapter_num} is empty or missing", "overall_score": 0.0}

    # Extract this chapter's outline entry (rough heuristic)
    outline = layers["outline"]
    ch_pattern = rf'###\s*Ch\s*{chapter_num}\b.*?(?=###\s*Ch\s*\d|## Act|## Foreshadowing|$)'
    ch_match = re.search(ch_pattern, outline, re.DOTALL)
    chapter_outline = ch_match.group(0) if ch_match else "(outline entry not found)"

    # Load previous chapter tail
    prev_text = load_chapter(chapter_num - 1) if chapter_num > 1 else "(first chapter)"
    prev_tail = prev_text[-3000:] if len(prev_text) > 3000 else prev_text       

    prompt = CHAPTER_PROMPT.format(
        voice=layers["voice"],
        world=layers["world"][:4000],
        characters=layers["characters"],
        canon=layers["canon"],
        chapter_outline=chapter_outline,
        prev_chapter_tail=prev_tail,
        chapter_text=chapter_text,
    )
    raw = call_judge(prompt, max_tokens=8000)
    result = parse_json_response(raw)

    # Mechanical slop check -- adjusts score independently of judge
    slop = slop_score(chapter_text)
    result["slop"] = slop
    if "overall_score" in result:
        adjusted = max(0, result["overall_score"] - slop["slop_penalty"])       
        result["raw_judge_score"] = result["overall_score"]
        result["overall_score"] = round(adjusted, 2)

    return result


# --- Full Novel Evaluation ---

FULL_NOVEL_PROMPT = """Evaluate this complete fantasy novel holistically.
You have the planning docs and ALL chapter summaries with their individual scores.

VOICE DEFINITION:
{voice}

WORLD BIBLE:
{world_summary}

CHARACTER REGISTRY:
{characters}

OUTLINE + FORESHADOWING LEDGER:
{outline}

CHAPTER SUMMARIES AND SCORES:
{chapter_summaries}

Score these novel-level dimensions 0-10:
- arc_completion: Do character arcs resolve satisfyingly?
- pacing_curve: Does tension build properly across the book?
- theme_coherence: Are themes explored consistently?
- foreshadowing_resolution: Are all planted threads harvested?
- world_consistency: Any lore contradictions across chapters?
- voice_consistency: Is the voice steady throughout?
- overall_engagement: Is this a compelling read start to finish?

Respond with JSON:
{{
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


def evaluate_full():
    layers = load_layer_files()
    chapters = load_all_chapters()

    if not chapters:
        return {"error": "No chapters found", "novel_score": 0.0}

    # Build chapter summaries (first/last 500 chars of each)
    summaries = []
    for num in sorted(chapters.keys()):
        text = chapters[num]
        word_count = len(text.split())
        head = text[:500]
        tail = text[-500:] if len(text) > 500 else ""
        summaries.append(
            f"Chapter {num} ({word_count} words):\n"
            f"  Opening: {head}...\n"
            f"  Closing: ...{tail}\n"
        )

    prompt = FULL_NOVEL_PROMPT.format(
        voice=layers["voice"],
        world_summary=layers["world"][:3000],
        characters=layers["characters"],
        outline=layers["outline"],
        chapter_summaries="\n".join(summaries),
    )
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

    # Print structured output
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

    # Save full eval log
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode = args.phase or (f"ch{args.chapter:02d}" if args.chapter else "full")  
    log_path = EVAL_LOG_DIR / f"{timestamp}_{mode}.json"
    with open(log_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\neval_log: {log_path}")


if __name__ == "__main__":
    main()
