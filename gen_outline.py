#!/usr/bin/env python3
"""
大纲生成器 - 从种子概念、世界设定、角色、谜团和写作技巧生成 章节大纲.md 文件。
"""
import logging
import os
import sys
from pathlib import Path

from api_client import call_llm, get_writer_model, get_api_key, get_api_provider, validate_api_config

BASE_DIR = Path(__file__).parent

# 新的目录结构
OUTPUT_DIR = BASE_DIR / "out_doc"
MD_FILES_DIR = OUTPUT_DIR / "md_file"

WRITER_MODEL = get_writer_model()
API_KEY = get_api_key()
API_PROVIDER = get_api_provider()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)

def call_writer(prompt, max_tokens=16000):
    """
    调用写作模型生成章节大纲内容。
    
    参数：
        prompt: 提示词字符串
        max_tokens: 生成的最大令牌数（默认16000）
    
    返回：
        生成的大纲文本
    """
    system_prompt = (
        "你是一位专业的小说架构师，精通Save the Cat节拍、桑德森的情节原则、Dan Harmon的故事圈和MICE商数。"
        "你构建的大纲让作者可以直接起草，无需临时发明结构。每章都有节拍、情感弧线和尝试-失败循环类型。"
        "你从不使用陈词滥调词汇。请用中文写作，风格简洁直接。"
    )
    return call_llm(prompt, WRITER_MODEL, max_tokens, temperature=0.5, system=system_prompt)

# 确保目录存在
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MD_FILES_DIR.mkdir(parents=True, exist_ok=True)

# 文件路径
SEED_FILE = OUTPUT_DIR / "seed.txt"
WORLD_FILE = MD_FILES_DIR / "世界设定.md"
CHARACTERS_FILE = MD_FILES_DIR / "角色设定.md"
MYSTERY_FILE = BASE_DIR / "MYSTERY.md"
VOICE_FILE = BASE_DIR / "voice.md"
CRAFT_FILE = BASE_DIR / "CRAFT.md"
OUTPUT_FILE = MD_FILES_DIR / "章节大纲.md"

# 验证API配置
validate_api_config()

if not API_KEY:
    logger.error(f"错误：请先在 .env 中设置 {'DEEPSEEK_API_KEY' if API_PROVIDER == 'deepseek' else 'ANTHROPIC_API_KEY'}")
    sys.exit(1)

# 检查必要文件
if not SEED_FILE.exists():
    logger.error(f"错误：未找到种子文件 {SEED_FILE}")
    sys.exit(1)

if not WORLD_FILE.exists():
    logger.error(f"错误：未找到世界设定文件 {WORLD_FILE}")
    logger.error("请先运行 gen_world.py 生成世界设定")
    sys.exit(1)

if not CHARACTERS_FILE.exists():
    logger.error(f"错误：未找到角色设定文件 {CHARACTERS_FILE}")
    logger.error("请先运行 gen_characters.py 生成角色设定")
    sys.exit(1)

if not MYSTERY_FILE.exists():
    logger.warning(f"警告：未找到 MYSTERY.md 文件，将使用空内容")
    mystery = ""
else:
    logger.info(f"加载谜团文件: {MYSTERY_FILE}")
    mystery = MYSTERY_FILE.read_text(encoding='utf-8')

logger.info(f"加载种子文件: {SEED_FILE}")
seed = SEED_FILE.read_text(encoding='utf-8')

logger.info(f"加载世界设定文件: {WORLD_FILE}")
world = WORLD_FILE.read_text(encoding='utf-8')

logger.info(f"加载角色设定文件: {CHARACTERS_FILE}")
characters = CHARACTERS_FILE.read_text(encoding='utf-8')

logger.info(f"加载写作技巧文件: {CRAFT_FILE}")
craft = CRAFT_FILE.read_text(encoding='utf-8')

logger.info(f"加载语音文件: {VOICE_FILE}")
voice = VOICE_FILE.read_text(encoding='utf-8')

# Voice Part 2 only
voice_lines = voice.split('\n')
part2_start = next(i for i, l in enumerate(voice_lines) if 'Part 2' in l or '第二部分' in l)
voice_part2 = '\n'.join(voice_lines[part2_start:])

prompt = f"""为这部小说构建完整的章节大纲。目标：20-26章，总计约80,000字（每章约3,000-4,000字）。

种子概念：
{seed}

核心谜团（仅供作者参考——读者逐步发现）：
{mystery}

世界圣经：
{world}

角色注册表：
{characters}

语音（基调和语域）：
{voice_part2}

写作技巧参考（遵循的结构）：
{craft}

构建大纲包含：

## 幕结构
规划第一幕（0-23%）、第二幕第一部分（23-50%）、第二幕第二部分（50-77%）、第三幕（77-100%）。
说明关键节点的百分比标记。

## 章节大纲

每章提供：
### Ch N: [标题]
- **POV:**（视角角色）
- **地点:** 哪些区域/位置
- **Save the Cat节拍:** 本章服务于哪个节拍（开场画面、铺垫、催化剂等）
- **%标记:** 在小说中的位置
- **情感弧线:** 起始情感 -> 结束情感
- **尝试-失败循环:** 是但 / 否且 / 否但 / 是且
- **节拍:** 3-5个必须发生的具体场景节拍
- **伏笔:** 本章植入的伏笔元素
- **回收:** 在本章回收的伏笔元素
- **角色发展:** 章节结束时角色发生什么变化
- **~字数目标:** 用于节奏控制

## 伏笔记录

追踪每个植入线索的表格：
| 线索 | 植入（章节） | 强化（章节） | 回收（章节） | 类型 |

至少包含15条线索。类型：物品、对话、动作、象征、结构。

关键情节架构：

第一幕（第1-6章左右）：建立主角的世界、他的痛苦、他的天赋、主要地点、他的家庭。
尽早植入谜团。催化剂：某事迫使主角开始调查。

第二幕第一部分（第7-12章左右）：调查。主角深入核心冲突，遇到对手，建立联盟。

第二幕第二部分（第13-18章左右）：压力加剧。对手采取行动。秘密开始浮出水面。
全失点：主角了解全部真相。

第三幕（第19-24章左右）：主角理解了问题。必须选择如何回答。高潮展开。结局展示选择的后果。

约束条件：
- 高潮必须能够使用既定规则机械解决
- 调查应该感觉像一个悬疑情节叠加在成长弧线上
- 稳定陷阱：坏事必须保持坏。并非一切都能干净解决。
- 至少3章应该是"安静的"——以角色为中心，低动作，情感丰富
- 变化尝试-失败类型：60%+应该是"是但"或"否且"
- 伏笔记录必须有至少3章的伏笔到回收距离
请用中文输出。
"""

logger.info(f"正在调用写作模型生成章节大纲...")
try:
    result = call_writer(prompt)
    
    logger.info(f"保存章节大纲到: {OUTPUT_FILE}")
    OUTPUT_FILE.write_text(result, encoding='utf-8')
    logger.info(f"章节大纲生成完成，字数: {len(result)}")
    
    print(result)
except Exception as e:
    logger.error(f"生成章节大纲时发生错误: {str(e)}", exc_info=True)
    sys.exit(1)