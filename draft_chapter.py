#!/usr/bin/env python3
"""
章节草稿生成器 - 使用写作模型生成单章草稿。
使用方法：python draft_chapter.py 1
"""
import os
import re
import sys
from pathlib import Path

from api_client import call_llm, get_writer_model, get_api_key, get_api_provider

BASE_DIR = Path(__file__).parent

WRITER_MODEL = get_writer_model()
API_KEY = get_api_key()
API_PROVIDER = get_api_provider()
CHAPTERS_DIR = BASE_DIR / "chapters"

def call_writer(prompt, max_tokens=16000):
    """
    调用写作模型生成章节草稿内容。
    
    参数：
        prompt: 提示词字符串
        max_tokens: 生成的最大令牌数（默认16000）
    
    返回：
        生成的章节文本
    """
    system_prompt = (
        "你是一位文学小说作家，正在撰写奇幻小说章节。"
        "你使用第三人称有限视角过去时态，锁定一个POV角色。"
        "你严格遵循语音定义。你命中大纲中的每个节拍。"
        "你从不使用禁用列表中的词汇。你展示，从不讲述情感。"
        "你的散文具体、感官化、接地气。比喻来自角色的经历。"
        "你变化句子长度。你信任读者。"
        "你写完整的章节——不要截断、总结或跳读。请用中文输出。"
    )
    return call_llm(prompt, WRITER_MODEL, max_tokens, temperature=0.8, system=system_prompt)

def load_file(path):
    """
    加载文件内容，如果文件不存在则返回空字符串。
    
    参数：
        path: 文件路径
    
    返回：
        文件内容字符串，文件不存在时返回空字符串
    """
    try:
        return Path(path).read_text()
    except FileNotFoundError:
        return ""

def extract_chapter_outline(outline_text, chapter_num):
    """
    从大纲文本中提取特定章节的大纲条目。
    
    参数：
        outline_text: 完整的大纲文本
        chapter_num: 章节号
    
    返回：
        章节大纲字符串，如果未找到则返回"(未找到)"
    """
    pattern = rf'### Ch {chapter_num}:.*?(?=### Ch {chapter_num + 1}:|## Foreshadowing|$)'
    match = re.search(pattern, outline_text, re.DOTALL)
    return match.group(0).strip() if match else "(未找到)"

def extract_next_chapter_outline(outline_text, chapter_num):
    """
    提取下一章的大纲（仅前几行用于保持连贯性）。
    
    参数：
        outline_text: 完整的大纲文本
        chapter_num: 当前章节号
    
    返回：
        下一章的前10行大纲，如果是最后一章则返回"(最后一章)"
    """
    next_entry = extract_chapter_outline(outline_text, chapter_num + 1)
    if next_entry == "(未找到)":
        return "(最后一章)"
    lines = next_entry.split('\n')[:10]
    return '\n'.join(lines)

def main():
    """
    主函数：生成指定章节的草稿。
    """
    if not API_KEY:
        print(f"错误：请先在 .env 中设置 {'DEEPSEEK_API_KEY' if API_PROVIDER == 'deepseek' else 'ANTHROPIC_API_KEY'}", file=sys.stderr)
        sys.exit(1)

    chapter_num = int(sys.argv[1])

    # 加载所有上下文
    voice = load_file(BASE_DIR / "voice.md")
    world = load_file(BASE_DIR / "world.md")
    characters = load_file(BASE_DIR / "characters.md")
    outline = load_file(BASE_DIR / "outline.md")
    canon = load_file(BASE_DIR / "canon.md")

    # 章节特定上下文
    chapter_outline = extract_chapter_outline(outline, chapter_num)
    next_chapter = extract_next_chapter_outline(outline, chapter_num)

    # 上一章（如果存在）
    prev_path = CHAPTERS_DIR / f"ch_{chapter_num - 1:02d}.md"
    if prev_path.exists():
        prev_text = prev_path.read_text()
        prev_tail = prev_text[-2000:] if len(prev_text) > 2000 else prev_text   
    else:
        prev_tail = "(第一章——无前章)"

    prompt = f"""撰写《贝尔之家的次子》第{chapter_num}章。

语音定义（严格遵循）：
{voice}

本章大纲（命中每个节拍）：
{chapter_outline}

下一章大纲（保持连贯性——结束本章以便流畅过渡到下一章）：
{next_chapter}

上一章结尾（从此继续）：
{prev_tail}

世界圣经（参考世界构建细节）：
{world}

角色注册表（参考说话模式和行为）：
{characters}

写作说明：
1. 写完整的章节。目标约3200字。不要截断或总结。
2. 第三人称有限视角，过去时态，锁定Cass的POV。
3. 按顺序命中大纲中的所有编号节拍。
4. 植入"Plants"下列出的所有伏笔元素。
5. 展示感官细节：Cass听到什么、闻到什么、身体感受到什么。
6. 不和谐音造成特定的身体疼痛（左眼后方的针刺感，不是模糊的不适）。
7. 对话遵循characters.md中定义的说话模式。
8. 不使用voice.md第1部分中的禁用词汇。
9. 不使用AI小说套路：不用"一种...的感觉"、"忍不住感到"、"眼睛睁大"等表达。
10. 变化句子长度。短句制造冲击力，长句用于铺垫。
11. 比喻来自Cass的经历：声音、青铜、工艺、身体对音调的反应。
12. 信任读者。不要解释场景的含义。让它们自然落地。
13. 从场景开始章节，不是叙述。以一个瞬间结束，不是总结。

要避免的模式（在前几章中已被标记）：
14. 不要使用三联感官列表。不要连续使用"X。Y。Z。"或"X和Y和Z"作为三个独立项目。合并两个，删除一个，或重新组织。
15. 每章"He did not [verb]"结构不超过一次。将否定转换为主动替代或直接删除。
16. 不要使用"He thought about [X]"结构。替换为：想法本身作为片段、身体动作或对话。
17. "the way [X] did [Y]"作为明喻连接词每章不超过两次。使用不同的明喻结构或删除比较。
18. 展示后不要过度解释。如果场景已经展示了某事，不要让叙述者重述。信任场景。
19. 不要将分段符（---）作为节奏拐杖。仅用于真正的时间/地点跳转。每章最多2次。
20. 有意变化段落长度。从不连续超过3个相似长度的段落。至少包含一个1-2句的段落和一个6句以上的段落。
21. 以一个安静观察的时刻结束章节——不是悬念，不是Cass在外面听父亲工作。找到属于本章的特定结局。
22. 包含至少一个令人惊讶的时刻——角色说错话、情感节拍提前或延迟到来、不符合预期模式的细节。可预测的优秀仍然是可预测的。
23. 优先场景而非总结。至少70%的章节应该是场景内（逐时刻，有对话和动作）而不是总结（叙述者压缩时间）。
24. 对话应该听起来像说话，不是散文。角色应该偶尔结巴、打断、拖尾或说些略微错误的话。一个14岁的孩子不会用优美的警句说话。

现在撰写章节。完整文本，从头到尾。请用中文输出。
"""

    print(f"正在起草第{chapter_num}章...", file=sys.stderr)
    result = call_writer(prompt)

    # 保存
    out_path = CHAPTERS_DIR / f"ch_{chapter_num:02d}.md"
    out_path.write_text(result)
    print(f"已保存到 {out_path}", file=sys.stderr)
    print(f"字数统计: {len(result.split())}", file=sys.stderr)
    print(result)

if __name__ == "__main__":
    main()
