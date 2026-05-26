#!/usr/bin/env python3
"""
Generate world building based on seed.
基于 seed.txt 生成完整小说世界观设定。
"""
import os
import sys
import logging
from pathlib import Path

from api_client import call_llm

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "out_doc"
MD_FILES_DIR = OUTPUT_DIR / "md_file"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MD_FILES_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)


def main():
    seed_path = OUTPUT_DIR / "seed.txt"

    if not seed_path.exists():
        logger.error(f"未找到 seed.txt：{seed_path}，请先在 out_doc 目录下创建该文件")
        return

    seed = seed_path.read_text(encoding="utf-8").strip()
    if not seed:
        logger.error("seed.txt 内容不能为空")
        return

    prompt = f"""你是专业小说世界观架构师，请根据以下灵感种子，生成详细、自洽、可用于小说创作的完整世界观设定。
包含：世界背景、地理格局、势力分布、力量体系、社会规则、核心冲突、特色设定。
要求：原创、严谨、细节丰富、中文写作，直接输出 Markdown 格式（不要 JSON）。

灵感种子：{seed}"""

    logger.info("正在生成世界观...")
    try:
        response = call_llm(prompt)
    except Exception as e:
        logger.error(f"调用 LLM 失败：{e}", exc_info=True)
        return

    if not response or not response.strip():
        logger.error("LLM 返回内容为空")
        return

    output_path = MD_FILES_DIR / "世界设定.md"
    try:
        output_path.write_text(response, encoding="utf-8")
        logger.info(f"世界观生成完成：{output_path}（字数：{len(response)}）")
    except Exception as e:
        logger.error(f"写入文件失败：{e}", exc_info=True)


if __name__ == "__main__":
    main()