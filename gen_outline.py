#!/usr/bin/env python3
"""
大纲生成器 - 平衡模式版本
适配「有质感的网文」：弹性开篇、情绪钩子，拒绝模板化
"""
import logging
import os
import sys
from pathlib import Path
from api_client import call_llm, get_writer_model, get_api_key, get_api_provider, validate_api_config

BASE_DIR = Path(__file__).parent
# 完全保留你原来的目录配置
OUTPUT_DIR = BASE_DIR / "out_doc"
MD_FILES_DIR = OUTPUT_DIR / "md_file"

WRITER_MODEL = get_writer_model()
API_KEY = get_api_key()
API_PROVIDER = get_api_provider()
# 模式配置，和draft统一
NOVEL_MODE = os.environ.get("AUTONOVEL_MODE", "balance").lower()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)

def call_writer(prompt, novel_type, max_tokens=20000):
    """
    调用写作模型生成适配的大纲
    """
    # 系统提示，根据模式切换
    if NOVEL_MODE == "shuangwen":
        system_prompt = f"""
你是一位精通中国本土小说创作的专业大纲设计师，擅长爽文小说的节奏设计。
你的大纲需要符合以下要求：
1. 符合国内读者的阅读习惯，节奏快，爽点密集
2. 黄金三章规则：前3章必须出冲突、金手指、第一个爽点
3. 每章都要设计爽点和钩子，让读者追更
4. 所有的节奏都要服务于剧情，避免俗套的重复
写作风格要求：
- 语言风格：简洁流畅的中文，符合网文创作习惯，避免欧化句式
- 细节要求：有具体的剧情节点，可直接用于章节生成
- 优先爽文的节奏，确保每章都有情绪点
当前创作类型：{novel_type}
"""
    elif NOVEL_MODE == "literature":
        system_prompt = f"""
你是一位专业的文学作家，正在设计小说大纲。
你的大纲需要符合西方三幕结构，节奏平缓，注重人物和主题。
写作风格要求：
- 语言风格：流畅的中文，注重文学性
- 细节要求：完整的三幕结构，人物弧光，主题表达
当前创作类型：{novel_type}
"""
    else: # balance 平衡模式，默认
        system_prompt = f"""
你是一位精通中国本土小说创作的专业大纲设计师，擅长有质感的网文创作。
你的大纲需要符合以下要求：
1. 优先保护用户的原创设定，禁止自动改成烂大街的穿越重生系统模板，突出原创脑洞
2. 弹性开篇规则：前3章必须抛出核心设定/悬念/冲突，抓住读者注意力，不用强制金手指
3. 每章都要设计一个情绪钩子：可以是悬念、脑洞、情感、世界观揭秘，优先用剧情做钩子，不用强制俗套的爽点
4. 章节大小：1500-2500字/章，弹性可调整，禁止拆分无关的小节点
5. 所有的节奏都要服务于剧情，禁止为了凑节奏，强行加无关的打脸/爽点
6. 伏笔设计：每3章埋一个小伏笔，每10章一个大伏笔，自然融入剧情
写作风格要求：
- 语言风格：简洁流畅的中文，符合网文创作习惯，避免欧化句式
- 细节要求：有具体的剧情节点，可直接用于章节生成
- 拒绝模板化，所有的设定都要突出用户的原创脑洞，避免千篇一律
当前创作类型：{novel_type}
"""
    return call_llm(prompt, WRITER_MODEL, max_tokens, temperature=0.75, system=system_prompt)

def load_file(path):
    """加载文件内容"""
    try:
        return Path(path).read_text(encoding='utf-8')
    except FileNotFoundError:
        return ""

def detect_novel_type(seed_text: str) -> str:
    """
    从种子文本中自动检测小说类型，完全保留你原来的检测逻辑
    """
    seed_lower = seed_text.lower()
    type_keywords = {
        "仙侠": ["修真", "修仙", "灵根", "宗门", "天劫", "道祖", "仙尊", "洪荒"],
        "武侠": ["武功", "门派", "江湖", "内功", "轻功", "侠客", "武林", "秘籍"],
        "都市": ["都市", "现代", "重生", "系统", "异能", "职场", "城市", "外卖"],
        "历史": ["朝代", "皇帝", "官场", "科举", "战争", "古风", "唐宋元明"],
        "玄幻": ["境界", "血脉", "武魂", "炼体", "位面", "神器", "妖族", "魔族"],
        "古风言情": ["后宫", "世家", "言情", "琴棋书画", "礼制", "王爷", "公主"]
    }
    
    type_scores = {novel_type: 0 for novel_type in ["仙侠", "武侠", "都市", "历史", "玄幻", "古风言情"]}
    for novel_type, keywords in type_keywords.items():
        for keyword in keywords:
            if keyword in seed_lower:
                type_scores[novel_type] += 1
    
    # 返回得分最高的类型，默认返回都市
    return max(type_scores, key=type_scores.get) if max(type_scores.values()) > 0 else "都市"

def generate_outline_prompt(seed: str, voice_part2: str, craft: str, novel_type: str, world: str, characters: str) -> str:
    """
    生成大纲的提示词，根据模式切换
    """
    if NOVEL_MODE == "shuangwen":
        return f"""
为这部{novel_type}爽文小说，生成完整的章节大纲，作为章节写作的指导。
【核心设定】
种子概念：
{seed}
【风格基调】
语音特征（小说的基调）：
{voice_part2}
【写作技巧】
{craft}
【世界设定】
{world}
【角色设定】
{characters}
【大纲规则】
1. 黄金三章：前3章必须出冲突→金手指→第一个爽点，3章抓住读者
2. 每章都要设计爽点和钩子，让读者想追更
3. 章节拆分：每章1500-2000字，用### 第N章 标题 的格式
4. 所有的节奏都要服务于剧情，禁止强行加无关的内容
5. 伏笔设计：自然的伏笔，不要太明显
请严格按照这个格式输出，用中文，清晰的章节拆分，每个章节下面写清楚剧情节点。
"""
    elif NOVEL_MODE == "literature":
        return f"""
为这部{novel_type}文学小说，生成完整的章节大纲，作为章节写作的指导。
【核心设定】
种子概念：
{seed}
【风格基调】
语音特征（小说的基调）：
{voice_part2}
【写作技巧】
{craft}
【世界设定】
{world}
【角色设定】
{characters}
【大纲规则】
1. 西方三幕结构，完整的人物弧光和主题表达
2. 章节拆分：每章3000字左右，用### 第N章 标题 的格式
3. 注重人物的成长和主题的探索
请严格按照这个格式输出，用中文，清晰的章节拆分，每个章节下面写清楚剧情节点。
"""
    else: # balance 平衡模式
        return f"""
为这部{novel_type}有质感的网文小说，生成完整的章节大纲，作为章节写作的指导。
【核心设定】
种子概念：
{seed}
【风格基调】
语音特征（小说的基调）：
{voice_part2}
【写作技巧】
{craft}
【世界设定】
{world}
【角色设定】
{characters}
【大纲规则（平衡模式）】
1. 优先保护用户的原创设定，禁止自动改成烂大街的穿越重生系统模板，突出你的原创脑洞
2. 弹性开篇：前3章必须抛出核心设定/悬念/冲突，抓住读者注意力，不用强制金手指
3. 每章都要设计一个情绪钩子：可以是悬念、脑洞、情感、世界观揭秘，优先用剧情做钩子，不用强制俗套的爽点
4. 章节拆分：每章1500-2500字，用### 第N章 标题 的格式，禁止拆分无关的小节点
5. 所有的节奏都要服务于剧情，禁止为了凑节奏，强行加无关的打脸/爽点
6. 伏笔设计：每3章埋一个小伏笔，每10章一个大伏笔，自然融入剧情，不要太明显
7. 禁止模板化，所有的剧情都要自然，避免千篇一律的重复
请严格按照这个格式输出，用中文，清晰的章节拆分，每个章节下面写清楚剧情节点，不要有多余的内容。
"""

def main():
    """主函数"""
    # 确保目录存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MD_FILES_DIR.mkdir(parents=True, exist_ok=True)
    
    # 验证API配置
    validate_api_config()
    if not API_KEY:
        logger.error(f"错误：请先在 .env 中设置 {'DEEPSEEK_API_KEY' if API_PROVIDER == 'deepseek' else 'ANTHROPIC_API_KEY'}")
        sys.exit(1)

    # 检查必要文件
    SEED_FILE = OUTPUT_DIR / "seed.txt"
    VOICE_FILE = BASE_DIR / "voice.md"
    CRAFT_FILE = BASE_DIR / "CRAFT.md"
    WORLD_FILE = MD_FILES_DIR / "世界设定.md"
    CHARACTERS_FILE = MD_FILES_DIR / "角色设定.md"
    
    required_files = [
        (SEED_FILE, "种子文件"),
        (VOICE_FILE, "语音文件"),
        (CRAFT_FILE, "写作技巧文件"),
        (WORLD_FILE, "世界设定文件"),
        (CHARACTERS_FILE, "角色设定文件")
    ]
    
    for file_path, file_desc in required_files:
        if not file_path.exists():
            logger.error(f"错误：未找到{file_desc} {file_path}")
            sys.exit(1)

    # 读取文件内容
    logger.info(f"加载种子文件: {SEED_FILE}")
    seed = SEED_FILE.read_text(encoding='utf-8')
    
    logger.info(f"加载语音文件: {VOICE_FILE}")
    voice = VOICE_FILE.read_text(encoding='utf-8')
    
    logger.info(f"加载写作技巧文件: {CRAFT_FILE}")
    craft = CRAFT_FILE.read_text(encoding='utf-8')
    
    logger.info(f"加载世界设定文件: {WORLD_FILE}")
    world = WORLD_FILE.read_text(encoding='utf-8')
    
    logger.info(f"加载角色设定文件: {CHARACTERS_FILE}")
    characters = CHARACTERS_FILE.read_text(encoding='utf-8')

    # 提取voice的第二部分
    voice_lines = voice.split('\n')
    try:
        part2_start = next(i for i, l in enumerate(voice_lines) if 'Part 2' in l or '第二部分' in l)
        voice_part2 = '\n'.join(voice_lines[part2_start:])
    except StopIteration:
        logger.warning("未找到Part 2/第二部分标记，使用完整语音文件内容")
        voice_part2 = voice

    # 自动检测小说类型，完全保留你原来的逻辑
    novel_type = detect_novel_type(seed)
    logger.info(f"自动检测到小说类型：{novel_type}，当前模式：{NOVEL_MODE}")

    # 生成定制化提示词
    prompt = generate_outline_prompt(seed, voice_part2, craft, novel_type, world, characters)

    # 调用模型生成内容
    logger.info(f"正在调用写作模型生成{novel_type}风格的大纲...")
    try:
        result = call_writer(prompt, novel_type)
        
        # 保存结果
        OUTPUT_FILE = MD_FILES_DIR / "章节大纲.md"
        logger.info(f"保存大纲到: {OUTPUT_FILE}")
        OUTPUT_FILE.write_text(result, encoding='utf-8')
        logger.info(f"大纲生成完成，字数: {len(result)}")
        
        print(f"\n===== {novel_type}风格大纲生成完成，模式：{NOVEL_MODE} =====")
        print(result)
        
    except Exception as e:
        logger.error(f"生成大纲时发生错误: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()