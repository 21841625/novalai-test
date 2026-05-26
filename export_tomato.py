#!/usr/bin/env python3
"""
番茄小说发布格式导出
一键导出纯文本，适配平台发布要求
"""
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent
CHAPTERS_DIR = BASE_DIR / "out_doc" / "chapters"

def clean_text(text):
    """清理markdown标记，去掉多余的格式"""
    # 去掉markdown的标题、加粗、斜体等
    text = re.sub(r'#+\s*', '', text)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'`(.*?)`', r'\1', text)
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    # 去掉多余的空行
    text = re.sub(r'\n\s*\n', r'\n\n', text)
    return text.strip()

def main():
    # 加载所有章节，按顺序排序
    chapters = []
    # 找中文章节
    for path in sorted(CHAPTERS_DIR.glob("第*章_*.md")):
        match = re.match(r'第(\d+)章_(.*?)\.md', path.name)
        if match:
            ch_num = int(match.group(1))
            ch_title = match.group(2)
            text = path.read_text(encoding='utf-8')
            cleaned = clean_text(text)
            chapters.append((ch_num, f"第{ch_num}章 {ch_title}", cleaned))
    
    if not chapters:
        # 兼容原来的英文章节
        for path in sorted(CHAPTERS_DIR.glob("ch_*.md")):
            match = re.match(r'ch_(\d+)\.md', path.name)
            if match:
                ch_num = int(match.group(1))
                text = path.read_text(encoding='utf-8')
                cleaned = clean_text(text)
                chapters.append((ch_num, f"第{ch_num}章", cleaned))
    
    if not chapters:
        print("错误：没有找到章节文件，请先生成章节")
        return
    
    # 排序
    chapters.sort(key=lambda x: x[0])
    
    # 合并
    output = []
    for ch_num, title, text in chapters:
        output.append(title)
        output.append("")
        output.append(text)
        output.append("")
        output.append("---")
        output.append("")
    
    # 保存
    out_path = BASE_DIR / "out_doc" / "番茄发布版.txt"
    out_path.write_text("\n".join(output), encoding='utf-8')
    
    print(f"✅ 番茄发布格式导出完成！")
    print(f"文件位置: {out_path}")
    print(f"共导出 {len(chapters)} 章，总字数: {len(''.join(output).split())}")

if __name__ == "__main__":
    main()