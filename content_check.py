#!/usr/bin/env python3
"""
内容合规检测
自动检测敏感词，确保过审
"""
import re
from pathlib import Path

# 基础敏感词库，你可以自己加
SENSITIVE_WORDS = {
    # 政治相关
    "敏感政治词1", "敏感政治词2",
    # 色情相关
    "敏感色情词1", "敏感色情词2",
    # 暴力相关
    "敏感暴力词1", "敏感暴力词2",
    # 其他违规
    "违规词1", "违规词2"
    # 你可以根据需要自己加更多
}

BASE_DIR = Path(__file__).parent
CHAPTERS_DIR = BASE_DIR / "out_doc" / "chapters"

def check_text(text, chapter_name):
    """检查单章的敏感词"""
    warnings = []
    lines = text.split('\n')
    for line_num, line in enumerate(lines, 1):
        for word in SENSITIVE_WORDS:
            if word in line:
                # 找到位置
                pos = line.find(word)
                # 上下文
                context = line[max(0, pos-20):min(len(line), pos+20)]
                warnings.append({
                    "line": line_num,
                    "word": word,
                    "context": context.strip()
                })
    return warnings

def main():
    print("=== 内容合规检测中... ===")
    all_warnings = []
    
    # 检查所有章节
    for path in sorted(CHAPTERS_DIR.glob("第*章_*.md")):
        ch_name = path.name
        print(f"检查 {ch_name}...")
        text = path.read_text(encoding='utf-8')
        warnings = check_text(text, ch_name)
        if warnings:
            all_warnings.append({
                "chapter": ch_name,
                "warnings": warnings
            })
    
    if not all_warnings:
        print("\n✅ 恭喜！没有检测到敏感词，内容合规！")
        return
    
    # 打印警告
    print("\n⚠️ 检测到敏感词，请修改：")
    for item in all_warnings:
        print(f"\n【{item['chapter']}】")
        for warn in item['warnings']:
            print(f"  第{warn['line']}行: 敏感词「{warn['word']}」，上下文: ...{warn['context']}...")
    
    print("\n提示：如果这些是误报，你可以自己修改SENSITIVE_WORDS列表去掉对应的词")

if __name__ == "__main__":
    main()