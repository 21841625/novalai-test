#!/usr/bin/env python3
"""
大纲生成器第二部分 - 生成剩余章节 + 伏笔记录。
"""
import logging
import os
import sys
import tempfile
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
    system_prompt = (
        "你是一位专业的小说架构师，正在继续编写大纲。请使用与前面章节相同的格式。"
        "每章需要：POV、地点、Save the Cat节拍、%标记、情感弧线、尝试-失败循环、"
        "节拍、伏笔、回收、角色发展、谎言、字数目标。"
    )
    return call_llm(prompt, WRITER_MODEL, max_tokens, 0.5, system_prompt)


def main():
    # 确保目录存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MD_FILES_DIR.mkdir(parents=True, exist_ok=True)
    
    # 文件路径
    OUTLINE_FILE = MD_FILES_DIR / "章节大纲.md"
    MYSTERY_FILE = BASE_DIR / "MYSTERY.md"
    
    # 验证API配置
    validate_api_config()

    if not API_KEY:
        logger.error(f"错误：请先在 .env 中设置 {'DEEPSEEK_API_KEY' if API_PROVIDER == 'deepseek' else 'ANTHROPIC_API_KEY'}")
        sys.exit(1)

    # 检查必要文件
    if not OUTLINE_FILE.exists():
        logger.error(f"错误：未找到章节大纲文件 {OUTLINE_FILE}")
        logger.error("请先运行 gen_outline.py 生成章节大纲")
        sys.exit(1)
    
    logger.info(f"加载章节大纲文件: {OUTLINE_FILE}")
    part1 = OUTLINE_FILE.read_text(encoding='utf-8')
    
    if not MYSTERY_FILE.exists():
        logger.warning(f"警告：未找到 MYSTERY.md 文件，将使用空内容")
        mystery = ""
    else:
        logger.info(f"加载谜团文件: {MYSTERY_FILE}")
        mystery = MYSTERY_FILE.read_text(encoding='utf-8')

    prompt = f"""以下是小说章节大纲的前半部分。请继续完成剩余章节，然后编写伏笔记录。

已有的大纲：
{part1}

核心谜团（供参考）：
{mystery}

需要完成的结构：

继续完成未完成的章节，然后完成后续章节，最后编写伏笔记录。

## 伏笔记录

| # | 线索 | 植入（章节） | 强化（章节） | 回收（章节） | 类型 |
|---|------|-------------|-----------------|-------------|------|

至少包含15条线索。类型：物品、对话、动作、象征、结构。
伏笔到回收的距离必须至少3章。

请用中文输出，保持与已有大纲相同的格式。
"""

    logger.info(f"正在调用写作模型完成章节大纲...")
    try:
        result = call_writer(prompt)
        
        # 将结果追加到章节大纲文件
        logger.info(f"追加内容到章节大纲: {OUTLINE_FILE}")
        with open(OUTLINE_FILE, 'a', encoding='utf-8') as f:
            f.write('\n\n' + result)
        
        logger.info(f"章节大纲第二部分生成完成")
        
        print(result)
    except Exception as e:
        logger.error(f"生成章节大纲第二部分时发生错误: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()