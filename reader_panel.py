#!/usr/bin/env python3
"""
读者评审团 - 平衡模式版本
双视角评估：网文追读读者 + 文学爱好者，自动检测俗套
"""
import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from api_client import call_llm, get_judge_model, get_api_key, get_api_provider

BASE_DIR = Path(__file__).parent
JUDGE_MODEL = get_judge_model()
API_KEY = get_api_key()
API_PROVIDER = get_api_provider()
# 模式配置，统一和其他脚本一致
NOVEL_MODE = os.environ.get("AUTONOVEL_MODE", "balance").lower()

CHAPTERS_DIR = BASE_DIR / "out_doc" / "chapters"
EVAL_LOG_DIR = BASE_DIR / "eval_logs"
EVAL_LOG_DIR.mkdir(exist_ok=True)

# 定义不同模式的评审人格
def get_panel_personas():
    if NOVEL_MODE == "shuangwen":
        # 爽文模式的评审人格
        return [
            {
                "name": "爽文老读者",
                "description": "你是一个看了10年爽文的老读者，最看重节奏和爽点，讨厌慢热和水字数，能一眼看出俗套的剧情",
                "criteria": "你只关心：1. 节奏够不够快？2. 爽点够不够密集？3. 钩子够不够强？4. 有没有水字数？",
                "weight": 0.6
            },
            {
                "name": "平台编辑",
                "description": "你是网文平台的资深编辑，熟悉平台的追读规则，知道什么样的内容能留住读者",
                "criteria": "你只关心：1. 开篇能不能抓住人？2. 每章有没有钩子？3. 节奏是不是符合平台要求？4. 有没有违规内容？",
                "weight": 0.4
            }
        ]
    elif NOVEL_MODE == "literature":
        # 文学模式的评审人格
        return [
            {
                "name": "文学评论家",
                "description": "你是一位资深文学评论家，擅长分析人物、主题和文笔，看重作品的文学价值",
                "criteria": "你只关心：1. 人物弧光够不够完整？2. 主题有没有深度？3. 文笔有没有质感？4. 有没有创意？",
                "weight": 0.7
            },
            {
                "name": "普通文学读者",
                "description": "你是一个喜欢读文学作品的普通读者，看重阅读体验和回味感",
                "criteria": "你只关心：1. 读起来有没有沉浸感？2. 看完能不能回味？3. 人物能不能共情？4. 有没有惊喜？",
                "weight": 0.3
            }
        ]
    else: # balance 平衡模式，默认
        # 平衡模式的双视角评审人格
        return [
            {
                "name": "网文追读读者",
                "description": "你是一个每天追更网文的读者，最看重节奏和钩子，讨厌慢热和水字数，能一眼看出有没有追读的欲望",
                "criteria": "你只关心：1. 节奏够不够紧凑？2. 结尾的钩子够不够强？3. 有没有水字数？4. 能不能让我想看下一章？",
                "weight": 0.5
            },
            {
                "name": "文学爱好者",
                "description": "你是一个喜欢有质感内容的读者，讨厌口水文和俗套，看重创意和深度，能一眼看出有没有内容质感",
                "criteria": "你只关心：1. 内容有没有创意？2. 人物够不够立体？3. 世界观有没有深度？4. 有没有烂大街的俗套？",
                "weight": 0.4
            },
            {
                "name": "反俗套检测者",
                "description": "你是一个专门检测俗套内容的人，看过太多烂大街的穿越重生系统模板，能一眼看出有没有模板化内容",
                "criteria": "你只关心：1. 有没有烂大街的俗套设定？2. 有没有反派降智/主角开挂的老套剧情？3. 有没有保护原创设定？4. 是不是千篇一律的模板？",
                "weight": 0.1
            }
        ]

def load_chapter(num):
    """加载章节，兼容中英文文件名"""
    # 先找中文文件名
    files = list(CHAPTERS_DIR.glob(f"第{num}章_*.md"))
    if files:
        return files[0].read_text()
    # 兼容原来的英文文件名
    path = CHAPTERS_DIR / f"ch_{num:02d}.md"
    return path.read_text() if path.exists() else ""

def get_panel_prompt(persona, chapter_text, chapter_outline):
    """生成单个人格的评估提示词"""
    return f"""
你是{persona['name']}，{persona['description']}
你的评估标准：{persona['criteria']}

现在给你一篇小说章节，你来给它打分，满分10分，0分最差，10分最好。
【章节大纲】
{chapter_outline}
【章节正文】
{chapter_text}

请你输出一个JSON格式的结果，不要有其他内容：
{{
  "persona": "{persona['name']}",
  "score": 你的打分(0-10的数字),
  "feedback": "你具体的反馈，要具体，不要空泛",
  "cliche_warnings": "你发现的俗套警告，如果没有就写空数组",
  "weight": {persona['weight']}
}}
"""

def evaluate_single_persona(persona, chapter_text, chapter_outline):
    """调用模型，单个人格的评估"""
    prompt = get_panel_prompt(persona, chapter_text, chapter_outline)
    raw = call_llm(prompt, JUDGE_MODEL, max_tokens=2000, temperature=0.3)
    # 解析JSON
    try:
        json_start = raw.find("{")
        json_end = raw.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            return json.loads(raw[json_start:json_end])
    except:
        pass
    return {"persona": persona['name'], "score": 5, "feedback": "解析失败", "cliche_warnings": [], "weight": persona['weight']}

def evaluate_chapter_panel(chapter_num):
    """整个评审团评估单章"""
    # 加载文件
    md_dir = BASE_DIR / "out_doc" / "md_file"
    outline_path = md_dir / "章节大纲.md"
    outline_text = outline_path.read_text() if outline_path.exists() else ""
    
    chapter_text = load_chapter(chapter_num)
    if not chapter_text.strip():
        return {"error": f"Chapter {chapter_num} is empty or missing", "panel_score": 0.0}
    
    # 提取章节大纲
    ch_pattern = rf'###\s*第{chapter_num}章.*?(?=###\s*第\d|## Act|## Foreshadowing|$)'
    ch_match = re.search(ch_pattern, outline_text, re.DOTALL)
    if not ch_match:
        ch_pattern = rf'###\s*Ch\s*{chapter_num}\b.*?(?=###\s*Ch\s*\d|## Act|## Foreshadowing|$)'
        ch_match = re.search(ch_pattern, outline_text, re.DOTALL)
    chapter_outline = ch_match.group(0) if ch_match else "(outline entry not found)"
    
    # 获取评审人格
    personas = get_panel_personas()
    results = []
    
    # 逐个评估
    for persona in personas:
        print(f"正在让 {persona['name']} 评估...")
        res = evaluate_single_persona(persona, chapter_text, chapter_outline)
        results.append(res)
    
    # 计算加权总分
    total_score = 0.0
    total_weight = 0.0
    all_cliche_warnings = []
    all_feedback = []
    
    for res in results:
        weight = res.get('weight', 0.33)
        score = res.get('score', 5)
        total_score += score * weight
        total_weight += weight
        if res.get('cliche_warnings'):
            all_cliche_warnings.extend(res['cliche_warnings'])
        all_feedback.append(f"[{res['persona']}] {res['feedback']}")
    
    panel_score = round(total_score / total_weight, 2) if total_weight > 0 else 5.0
    
    return {
        "panel_results": results,
        "panel_score": panel_score,
        "cliche_warnings": list(set(all_cliche_warnings)), # 去重
        "all_feedback": all_feedback,
        "mode": NOVEL_MODE
    }

def main():
    parser = argparse.ArgumentParser(description="读者评审团评估")
    parser.add_argument("--chapter", type=int, required=True, help="要评估的章节号")
    args = parser.parse_args()

    if not API_KEY:
        print(f"ERROR: Set {'DEEPSEEK_API_KEY' if API_PROVIDER == 'deepseek' else 'ANTHROPIC_API_KEY'} in .env first", file=sys.stderr)
        sys.exit(1)

    print(f"=== 读者评审团评估，模式：{NOVEL_MODE} ===")
    result = evaluate_chapter_panel(args.chapter)
    
    # 打印结果
    print("\n--- 评估结果 ---")
    print(f"评审团总分: {result['panel_score']}")
    for res in result['panel_results']:
        print(f"{res['persona']}: {res['score']}分 - {res['feedback']}")
    
    if result['cliche_warnings']:
        print("\n⚠️ 俗套警告:")
        for warn in result['cliche_warnings']:
            print(f"  - {warn}")
    
    # 保存日志
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = EVAL_LOG_DIR / f"{timestamp}_panel_ch{args.chapter:02d}_{NOVEL_MODE}.json"
    with open(log_path, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n评估日志已保存到: {log_path}")

if __name__ == "__main__":
    # 导入re，因为上面用了re.search
    import re
    main()