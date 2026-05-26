#!/usr/bin/env python3
"""
典章生成器 - 从世界设定和角色设定中提取所有硬事实，生成 典章.md 文件。
"""
import logging
import os
import sys
from pathlib import Path

from api_client_1 import call_llm, get_writer_model, get_api_key, get_api_provider, validate_api_config

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
    调用写作模型生成典章内容。
    
    参数：
        prompt: 提示词字符串
        max_tokens: 生成的最大令牌数（默认16000）
    
    返回：
        生成的典章文本
    """
    system_prompt = (
        "你是一位专业的小说连续性编辑，从小说规划文档中提取硬事实。"
        "你精准、详尽，从不编造来源材料中没有的事实。"
        "每个条目都必须能够追溯到源文档中的特定陈述。"
    )
    return call_llm(prompt, WRITER_MODEL, max_tokens, temperature=0.2, system=system_prompt)

# 确保目录存在
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MD_FILES_DIR.mkdir(parents=True, exist_ok=True)

# 文件路径
SEED_FILE = OUTPUT_DIR / "seed.txt"
WORLD_FILE = MD_FILES_DIR / "世界设定.md"
CHARACTERS_FILE = MD_FILES_DIR / "角色设定.md"
OUTPUT_FILE = MD_FILES_DIR / "典章.md"

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

logger.info(f"加载种子文件: {SEED_FILE}")
seed = SEED_FILE.read_text(encoding='utf-8')

logger.info(f"加载世界设定文件: {WORLD_FILE}")
world = WORLD_FILE.read_text(encoding='utf-8')

logger.info(f"加载角色设定文件: {CHARACTERS_FILE}")
characters = CHARACTERS_FILE.read_text(encoding='utf-8')

prompt = f"""从这些规划文档中提取每一个硬事实，整理成结构化的典章数据库。
"硬事实"是作者不能矛盾的任何内容：名称、年龄、日期、物理描述、
特殊系统规则、地理、关系、既定事件。

源文档：

=== SEED.TXT ===
{seed}

=== 世界设定.md ===
{world}

=== 角色设定.md ===
{characters}

将输出格式化为 典章.md，包含以下类别：

## 地理
- 关于地点、距离、物理属性的具体事实

## 时间线
- 日期事件、年龄、持续时间

## 特殊系统
- 特殊能力的硬规则（间隔、代价、限制）
- 主角天赋的具体细节

## 角色事实
- 年龄、物理描述、习惯、关系
- 每个事实一个条目（不要段落）

## 政治/派系
- 谁控制什么、联盟、冲突、契约

## 文化
- 习俗、禁忌、法律、节日、食物、服装

## 故事背景
- 在故事过去已经发生的事件

规则：
- 每个项目符号一个事实。简短、具体、可检查。
- 在每个事实后注明来源（世界设定.md 或 角色设定.md）。
- 目标至少 80-120 条条目。要详尽。
- 如果两个文档提供略有不同的细节，注明差异。
- 不要编造事实。只记录明确说明的内容。
请用中文输出。
"""

logger.info(f"正在调用写作模型生成典章...")
try:
    result = call_writer(prompt)
    
    logger.info(f"保存典章到: {OUTPUT_FILE}")
    OUTPUT_FILE.write_text(result, encoding='utf-8')
    logger.info(f"典章生成完成，字数: {len(result)}")
    
    print(result)
except Exception as e:
    logger.error(f"生成典章时发生错误: {str(e)}", exc_info=True)
    sys.exit(1)