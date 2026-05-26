#!/usr/bin/env python3
"""
章节草稿生成器 - 平衡模式版本
适配「有质感的网文」：既有追读节奏，又保留内容质感，拒绝口水文
"""
import logging
import os
import re
import sys
from pathlib import Path
from api_client import call_llm, get_writer_model, get_api_key, get_api_provider, validate_api_config

BASE_DIR = Path(__file__).parent
# 新的目录结构（完全保留你原来的配置）
OUTPUT_DIR = BASE_DIR / "out_doc"
MD_FILES_DIR = OUTPUT_DIR / "md_file"
CHAPTERS_DIR = OUTPUT_DIR / "chapters"

WRITER_MODEL = get_writer_model()
API_KEY = get_api_key()
API_PROVIDER = get_api_provider()

# 读取模式配置：在.env里加 AUTONOVEL_MODE=balance 即可
# 可选模式：balance(平衡模式，默认) / shuangwen(爽文模式) / literature(文学模式)
NOVEL_MODE = os.environ.get("AUTONOVEL_MODE", "balance").lower()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)

def call_writer(prompt, max_tokens=16000):
    """
    调用写作模型生成章节草稿内容。
    """
    # 系统提示：根据模式自动切换
    if NOVEL_MODE == "shuangwen":
        system_prompt = (
            "你是一位专业的网文作家，正在撰写爽文小说章节。"
            "你使用第三人称有限视角过去时态，锁定一个POV角色。"
            "你严格遵循语音定义。你命中大纲中的每个节拍。"
            "你从不使用禁用列表中的词汇。你展示，从不讲述情感。"
            "你的散文具体、感官化、接地气。比喻来自角色的经历。"
            "你变化句子长度。你信任读者。"
            "你写完整的章节——不要截断、总结或跳读。请用中文输出。"
        )
    elif NOVEL_MODE == "literature":
        system_prompt = (
            "你是一位专业的文学作家，正在撰写小说章节。"
            "你使用第三人称有限视角过去时态，锁定一个POV角色。"
            "你严格遵循语音定义。你命中大纲中的每个节拍。"
            "你从不使用禁用列表中的词汇。你展示，从不讲述情感。"
            "你的散文具体、感官化、接地气。比喻来自角色的经历。"
            "你变化句子长度。你信任读者。"
            "你写完整的章节——不要截断、总结或跳读。请用中文输出。"
        )
    else: # balance 平衡模式，默认
        system_prompt = (
            "你是一位专业的网文作家，正在撰写有质感的小说章节。"
            "你使用第三人称有限视角过去时态，锁定一个POV角色。"
            "你严格遵循语音定义。你命中大纲中的每个节拍。"
            "你从不使用禁用列表中的词汇。你展示，从不讲述情感。"
            "你的散文具体、感官化、接地气。比喻来自角色的经历。"
            "你变化句子长度。你信任读者。"
            "优先保留原创设定，拒绝俗套的模板化内容。"
            "你写完整的章节——不要截断、总结或跳读。请用中文输出。"
        )
    return call_llm(prompt, WRITER_MODEL, max_tokens, temperature=0.8, system=system_prompt)

def load_file(path):
    """
    加载文件内容，如果文件不存在则返回空字符串。
    """
    try:
        return Path(path).read_text(encoding='utf-8')
    except FileNotFoundError:
        return ""

def extract_chapter_outline(outline_text, chapter_num):
    """
    从大纲文本中提取特定章节的大纲条目。
    支持英文格式 "Ch N" 和中文格式 "第N章"
    """
    patterns = [
        rf'### Ch {chapter_num}:.*?(?=### Ch {chapter_num + 1}:|## |$)',
        rf'### 第{chapter_num}章.*?(?=### 第{chapter_num + 1}章|## |$)'
    ]
    for pattern in patterns:
        match = re.search(pattern, outline_text, re.DOTALL)
        if match:
            return match.group(0).strip()
    return "(未找到)"

def extract_chapter_title(outline_text, chapter_num):
    """
    从大纲中提取章节标题。
    """
    patterns = [
        rf'### Ch {chapter_num}:\s*(.*?)\s*-',
        rf'### 第{chapter_num}章\s*[:：]\s*(.*?)\s*-',
        rf'### Ch {chapter_num}:\s*(.*?)$',
        rf'### 第{chapter_num}章\s*[:：]\s*(.*?)$'
    ]
    for pattern in patterns:
        match = re.search(pattern, outline_text, re.MULTILINE)
        if match:
            return match.group(1).strip()
    return ""

def extract_next_chapter_outline(outline_text, chapter_num):
    """
    提取下一章的大纲（仅前几行用于保持连贯性）。
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
    # 确保目录存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MD_FILES_DIR.mkdir(parents=True, exist_ok=True)
    CHAPTERS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 验证API配置
    validate_api_config()
    if not API_KEY:
        logger.error(f"错误：请先在 .env 中设置 {'DEEPSEEK_API_KEY' if API_PROVIDER == 'deepseek' else 'ANTHROPIC_API_KEY'}")
        sys.exit(1)

    if len(sys.argv) < 2:
        logger.error("错误：请指定章节号，用法：python draft_chapter.py 1")
        sys.exit(1)
    try:
        chapter_num = int(sys.argv[1])
    except ValueError:
        logger.error(f"错误：章节号必须是数字，输入: {sys.argv[1]}")
        sys.exit(1)

    # 加载所有上下文
    logger.info(f"加载语音文件...")
    voice = load_file(BASE_DIR / "voice.md")
    
    logger.info(f"加载世界设定文件...")
    world = load_file(MD_FILES_DIR / "世界设定.md")
    
    logger.info(f"加载角色设定文件...")
    characters = load_file(MD_FILES_DIR / "角色设定.md")
    
    logger.info(f"加载章节大纲文件...")
    outline = load_file(MD_FILES_DIR / "章节大纲.md")
    
    logger.info(f"加载典章文件...")
    canon = load_file(MD_FILES_DIR / "典章.md")

    # 检查必要文件
    if not world:
        logger.error("错误：世界设定文件为空或不存在")
        sys.exit(1)
    
    if not characters:
        logger.error("错误：角色设定文件为空或不存在")
        sys.exit(1)
    
    if not outline:
        logger.error("错误：章节大纲文件为空或不存在")
        sys.exit(1)

    # 章节特定上下文
    chapter_outline = extract_chapter_outline(outline, chapter_num)
    chapter_title = extract_chapter_title(outline, chapter_num)
    next_chapter = extract_next_chapter_outline(outline, chapter_num)

    # 上一章（如果存在）
    prev_path = None
    prev_files = list(CHAPTERS_DIR.glob(f"第{chapter_num - 1}章_*.md"))
    if prev_files:
        prev_path = prev_files[0]
    
    if prev_path and prev_path.exists():
        prev_text = prev_path.read_text(encoding='utf-8')
        prev_tail = prev_text[-2000:] if len(prev_text) > 2000 else prev_text
    else:
        prev_tail = "(第一章——无前章)"

    # 构建章节标题
    if chapter_title:
        chapter_title_full = f"第{chapter_num}章_{chapter_title}"
    else:
        chapter_title_full = f"第{chapter_num}章_未命名"

    # 生成提示词，根据模式切换规则
    if NOVEL_MODE == "shuangwen":
        # 爽文模式的提示
        prompt = f"""撰写小说第{chapter_num}章。
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
1. 写完整的章节。目标约1800字。不要截断或总结。
2. 第三人称有限视角，过去时态，锁定主角的POV。
3. 按顺序命中大纲中的所有编号节拍。
4. 植入"伏笔"下列出的所有伏笔元素。
5. 展示感官细节：主角听到什么、闻到什么、身体感受到什么。
6. 对话遵循角色设定中定义的说话模式。
7. 不使用voice.md第1部分中的禁用词汇。
8. 不使用AI小说套路：不用"一种...的感觉"、"忍不住感到"、"眼睛睁大"等表达。
9. 变化句子长度。短句制造冲击力，长句用于铺垫。
10. 比喻来自主角的经历和背景。
11. 信任读者。不要解释场景的含义。让它们自然落地。
12. 从场景开始章节，不是叙述。以一个爽点/钩子结束，让读者想看下一章。
要避免的模式：
13. 不要使用三联感官列表。不要连续使用"X。Y。Z。"或"X和Y和Z"作为三个独立项目。合并两个，删除一个，或重新组织。
14. 每章"He did not [verb]"结构不超过一次。将否定转换为主动替代或直接删除。
15. 不要使用"He thought about [X]"结构。替换为：想法本身作为片段、身体动作或对话。
16. "the way [X] did [Y]"作为明喻连接词每章不超过两次。使用不同的明喻结构或删除比较。
17. 展示后不要过度解释。如果场景已经展示了某事，不要让叙述者重述。信任场景。
18. 不要将分段符（---）作为节奏拐杖。仅用于真正的时间/地点跳转。每章最多2次。
19. 有意变化段落长度。从不连续超过3个相似长度的段落。至少包含一个1-2句的段落和一个6句以上的段落。
20. 结尾必须留一个爽点/钩子，让读者想追更，所有钩子都要服务于剧情。
21. 每章至少有一个情绪爽点，自然来自剧情。
22. 优先场景而非总结。至少70%的章节应该是场景内（逐时刻，有对话和动作）而不是总结（叙述者压缩时间）。
23. 对话应该听起来像说话，不是散文。角色应该偶尔结巴、打断、拖尾或说些略微错误的话。
现在撰写章节。完整文本，从头到尾。请用中文输出。
"""
    elif NOVEL_MODE == "literature":
        # 文学模式的提示，原来的规则
        prompt = f"""撰写小说第{chapter_num}章。
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
2. 第三人称有限视角，过去时态，锁定主角的POV。
3. 按顺序命中大纲中的所有编号节拍。
4. 植入"伏笔"下列出的所有伏笔元素。
5. 展示感官细节：主角听到什么、闻到什么、身体感受到什么。
6. 对话遵循角色设定中定义的说话模式。
7. 不使用voice.md第1部分中的禁用词汇。
8. 不使用AI小说套路：不用"一种...的感觉"、"忍不住感到"、"眼睛睁大"等表达。
9. 变化句子长度。短句制造冲击力，长句用于铺垫。
10. 比喻来自主角的经历和背景。
11. 信任读者。不要解释场景的含义。让它们自然落地。
12. 从场景开始章节，不是叙述。以一个安静观察的时刻结束章节——不是悬念，不是总结。找到属于本章的特定结局。
要避免的模式：
13. 不要使用三联感官列表。不要连续使用"X。Y。Z。"或"X和Y和Z"作为三个独立项目。合并两个，删除一个，或重新组织。
14. 每章"He did not [verb]"结构不超过一次。将否定转换为主动替代或直接删除。
15. 不要使用"He thought about [X]"结构。替换为：想法本身作为片段、身体动作或对话。
16. "the way [X] did [Y]"作为明喻连接词每章不超过两次。使用不同的明喻结构或删除比较。
17. 展示后不要过度解释。如果场景已经展示了某事，不要让叙述者重述。信任场景。
18. 不要将分段符（---）作为节奏拐杖。仅用于真正的时间/地点跳转。每章最多2次。
19. 有意变化段落长度。从不连续超过3个相似长度的段落。至少包含一个1-2句的段落和一个6句以上的段落。
20. 以一个安静观察的时刻结束章节——不是悬念，不是总结。找到属于本章的特定结局。
21. 包含至少一个令人惊讶的时刻——角色说错话、情感节拍提前或延迟到来、不符合预期模式的细节。可预测的优秀仍然是可预测的。
22. 优先场景而非总结。至少70%的章节应该是场景内（逐时刻，有对话和动作）而不是总结（叙述者压缩时间）。
23. 对话应该听起来像说话，不是散文。角色应该偶尔结巴、打断、拖尾或说些略微错误的话。
现在撰写章节。完整文本，从头到尾。请用中文输出。
"""
    else:
        # 平衡模式，默认，我们要的模式
        prompt = f"""撰写小说第{chapter_num}章。
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
1. 写完整的章节。字数1500-2500字，**禁止水字数**，每一段内容都要有价值，要么推进剧情，要么塑造人物，要么铺垫世界观。
2. 第三人称有限视角，过去时态，锁定主角的POV。
3. 按顺序命中大纲中的所有编号节拍。
4. 植入"伏笔"下列出的所有伏笔元素。
5. 展示感官细节：主角听到什么、闻到什么、身体感受到什么。
6. 对话遵循角色设定中定义的说话模式。
7. 不使用voice.md第1部分中的禁用词汇。
8. 不使用烂大街的AI套路：不用"一种...的感觉"、"忍不住感到"、"眼睛睁大"等烂大街表达。
9. 变化句子长度。短句制造冲击力，长句用于铺垫，优先短句，符合网文阅读习惯。
10. 比喻来自主角的经历和背景，不要用烂大街的比喻。
11. 信任读者。不要解释场景的含义。让它们自然落地。
12. 从场景开始章节，不是叙述。**结尾必须留一个情绪钩子**，可以是悬念、脑洞、情感、世界观揭秘，所有钩子都要服务于剧情，禁止强行加无关的悬念。
要避免的模式：
13. 不要使用三联感官列表。不要连续使用"X。Y。Z。"或"X和Y和Z"作为三个独立项目。合并两个，删除一个，或重新组织。
14. 每章否定句结构不超过一次。将否定转换为主动替代或直接删除。
15. 不要使用"他想到了[X]"这种结构。替换为：想法本身作为片段、身体动作或对话。
16. 烂大街的明喻连接词每章不超过两次。使用不同的明喻结构或删除比较。
17. 展示后不要过度解释。如果场景已经展示了某事，不要让叙述者重述。信任场景。
18. 不要将分段符（---）作为节奏拐杖。仅用于真正的时间/地点跳转。每章最多2次。
19. 有意变化段落长度。从不连续超过3个相似长度的段落。至少包含一个1-2句的段落和一个6句以上的段落。
20. **禁止为了凑规则，强行加俗套的打脸/开挂/爽点**，所有的情绪都要自然来自剧情，禁止为了规则而规则。
21. 优先保护你的原创设定，禁止自动改成烂大街的穿越重生系统模板，突出你的原创脑洞。
22. 优先场景而非总结。至少70%的章节应该是场景内（逐时刻，有对话和动作）而不是总结（叙述者压缩时间）。
23. 对话应该听起来像说话，不是散文。角色应该偶尔结巴、打断、拖尾或说些略微错误的话，符合人物的性格。
现在撰写章节。完整文本，从头到尾。请用中文输出。
"""

    logger.info(f"正在起草第{chapter_num}章...")
    try:
        result = call_writer(prompt)
        # 保存
        out_path = CHAPTERS_DIR / f"{chapter_title_full}.md"
        out_path.write_text(result, encoding='utf-8')
        logger.info(f"已保存到 {out_path}")
        logger.info(f"字数统计: {len(result.split())}")
        print(result)
    except Exception as e:
        logger.error(f"生成章节草稿时发生错误: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()