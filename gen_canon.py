#!/usr/bin/env python3
"""
Generate canon.md by extracting all hard facts from world.md + characters.md.   
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
    system_prompt = (
        "You are a continuity editor extracting hard facts from fantasy novel "
        "planning documents. You are precise, exhaustive, and never invent facts "
        "that aren't in the source material. Every entry must be traceable to a "
        "specific statement in the source documents."
    )
    return call_llm(prompt, WRITER_MODEL, max_tokens, temperature=0.2, system=system_prompt)

world = (BASE_DIR / "world.md").read_text()
characters = (BASE_DIR / "characters.md").read_text()
seed = (BASE_DIR / "seed.txt").read_text()

prompt = f"""Extract EVERY hard fact from these planning documents into a structured canon database.
A "hard fact" is anything a writer must not contradict: names, ages, dates, physical descriptions,
rules of the magic system, geography, relationships, established events.        

SOURCE DOCUMENTS:

=== SEED.TXT ===
{seed}

=== WORLD.MD ===
{world}

=== CHARACTERS.MD ===
{characters}

FORMAT THE OUTPUT AS CANON.MD with these categories:

## Geography
- Specific facts about locations, distances, physical properties

## Timeline
- Dated events, ages, durations

## Magic System
- Hard rules of Tonal Law (intervals, costs, limitations)
- Cass's gift specifics

## Character Facts
- Ages, physical descriptions, habits, relationships
- One entry per fact (not paragraphs)

## Political / Factional
- Who controls what, alliances, conflicts, contracts

## Cultural
- Customs, taboos, laws, festivals, food, clothing

## Established In-Story
- Events that have already happened in the story's past
- The Perin contract, the Expansion Wars, etc.

RULES:
- One fact per bullet point. Short. Specific. Checkable.
- Include the source (world.md or characters.md) in parentheses after each fact.
- Aim for 80-120 entries minimum. Be exhaustive.
- If two documents give slightly different details, note the discrepancy.       
- DO NOT invent facts. Only record what's explicitly stated.
"""

if not API_KEY:
    print(f"ERROR: Set {'DEEPSEEK_API_KEY' if API_PROVIDER == 'deepseek' else 'ANTHROPIC_API_KEY'} in .env first", file=sys.stderr)
    sys.exit(1)

print("Calling writer model...", file=sys.stderr)
result = call_writer(prompt)
print(result)
