#!/usr/bin/env python3
"""
Generate world building based on seed.
基于 seed.txt 生成立项阶段（MVP）的小说世界观设定。

核心设计：
1. MVP 立项原则：只锚定前 10 章必需的设定，大部分细节留作"地图迷雾"
2. 完全尊重 seed.txt 中已经确定的主角/副本/NPC/金句，不擅自扩展
3. 输出文件版本管理：若已存在 世界设定.md，则自动递增版本号
   (世界设定_v1.md, 世界设定_v2.md ...)
"""
import os
import re
import sys
import logging
from pathlib import Path

from api_client import call_llm

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "out_doc"
MD_FILES_DIR = OUTPUT_DIR / "md_file"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MD_FILES_DIR.mkdir(parents=True, exist_ok=True)

# 输出文件基础名称（不含版本号和扩展名）
OUTPUT_BASE_NAME = "世界设定"
OUTPUT_EXT = ".md"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)


def get_next_output_path(base_dir: Path, base_name: str, ext: str) -> Path:
    """
    版本管理：根据已存在的文件，自动生成下一个版本的文件名。

    规则：
        - 若 base_name.ext 不存在，返回 base_name.ext
        - 若已存在，扫描 base_name_v*.ext 找到最大版本号 N，返回 base_name_v{N+1}.ext
        - 例如：已存在 世界设定.md 和 世界设定_v2.md，则返回 世界设定_v3.md
    """
    base_path = base_dir / f"{base_name}{ext}"
    if not base_path.exists():
        return base_path

    pattern = re.compile(rf"^{re.escape(base_name)}_v(\d+){re.escape(ext)}$")
    max_version = 0
    for p in base_dir.iterdir():
        if not p.is_file():
            continue
        m = pattern.match(p.name)
        if m:
            try:
                v = int(m.group(1))
                if v > max_version:
                    max_version = v
            except ValueError:
                continue

    next_version = max_version + 1
    return base_dir / f"{base_name}_v{next_version}{ext}"


def build_prompt(seed: str) -> str:
    """
    构建世界观生成提示词（MVP 立项版 · 适配前 10 章聚焦）。

    核心原则：
    - 立项阶段不要"上帝模式开太满"，只锚定前 10 章必需的设定
    - 大部分世界细节保留为"迷雾"，等剧情推进自然浮现
    - 严格遵循 seed.txt 中已经确定的所有设定，不要扩展或更改
    """
    return f"""你是一位资深网文世界观策划，正在协助作者完成【立项阶段】的世界观文档。

# 当前阶段定位
这是【MVP 立项】，不是【全书架构】。
目标是产出一份**适合前 10 章、约 3 万字**的世界观文档，
让作者能马上开始动笔，**不需要一上来就锁死全书 100 章的所有细节**。

# 输出原则（非常重要，请严格遵守）

1. **完全尊重 seed.txt 中已经确定的内容**
   - 主角姓名、性格、自述、看家本领（伪学究式机灵）→ 不得更改
   - 第一个副本【末日图书馆】的规则、特征、NPC、危险 → 不得更改
   - 关键 NPC 沈知白的人设、初见场景 → 不得更改
   - 5 条伪学究金句锚点 → 直接引用，不要重写
   - 风格 DNA 5 条规则 → 严格遵守

2. **只在 seed 已有信息基础上做"恰到好处的延展"**
   - 不要发明 seed 中没出现的大设定（如"概念融合""万法归一""异化倒计时"）
   - 不要扩展副本数量（只写第一个副本【末日图书馆】的详细设计）
   - 不要扩展女性角色（只写沈知白这一个）
   - 不要给出全书反派、终局、本源真相

3. **"刻意留空的迷雾"原则**
   - seed.txt 中明确列出的"刻意留空的迷雾"——这些**绝对不要在本次输出中揭晓答案**
   - 可以暗示这些悬念的存在，但不要给出真相

4. **输出格式要求**
   - 直接输出 Markdown，不要 JSON、不要代码块包裹
   - 全文简体中文，符合中文网文阅读习惯
   - 关键概念可加粗，用表格、列表、段落混排

# 章节结构（请严格按此输出，每节都聚焦"前 10 章必需"）

## 一、主角档案（基于 seed 扩展）
- 陈末的更多生活细节：住哪、吃什么、欠了谁的钱、口头禅、招牌动作
- 陈末的怂智慧具体表现：在遇到危险时的 3 种典型反应
- 陈末说出伪学究金句的"触发条件"——什么场景下会冒出来
- 注意：不要美化主角，也不要把主角写成丧文青；他是穷得清醒的打工人

## 二、灾调局（仅限前 10 章会接触到的部分）
- 灾调局对外的伪装身份是什么？
- 陈末的入职流程（传单 → 签约 → 第一次任务派遣）
- 临时工的工资结构、绩效考核、年终奖
- 陈末的"工位"长什么样
- 与陈末直接对接的"HR/主管"是谁？此人是什么性格？
- 注意：高层局长、其他正式员工、特勤等都不要展开，留迷雾

## 三、第一个副本【末日图书馆】的详细化（基于 seed 已有设定扩展）
- 副本入口在主世界的哪个位置？
- 副本里的"层数划分"具体长什么样？前 10 章会经过哪几层？
- 【未读者】的形态描述、攻击方式、弱点
- 【最后的章节】的具体表现形式
- 沈知白在副本里的"日常"（除了煮泡面，还干什么）
- 副本里有哪些"被遗忘的书页"陈末可能捡到？

## 四、关键 NPC · 沈知白
- 完整背景（外貌、口头禅、穿着习惯、生活方式）
- 她和陈末的相处模式细化（毒舌但护短的具体表现）
- 她对陈末的"潜在好感"如何在前 10 章一点点露出端倪
- 她为什么会出现在末日图书馆这个副本？

## 五、伪学究金句使用指南（写作时的执行手册）
- 直接引用 seed.txt 中的 5 条锚点金句
- 解释每条金句适合在什么场景出现
- 给出"前 10 章每章至少 1 句"的可化用金句模板（不要再发明新金句，只给"模板"）
- 反复强调 seed.txt 中的"风格 DNA 5 条规则"

## 六、前 10 章的"伏笔种子"（只列前 10 章会撒下的伏笔，不揭晓答案）
- 第一类伏笔：陈末工位上一任的痕迹（贴纸、抽屉里的纸条、键盘的磨损）
- 第二类伏笔：沈知白说漏嘴的几次（"前任 D 级"是什么意思？）
- 第三类伏笔：副本结算单上的"隐藏标注"
- 第四类伏笔：灾调局食堂的奇怪闲谈
- 注意：每个伏笔都只描述"埋"，不描述"挖"——答案留到后续章节

## 七、刻意留空（请在输出中明确说明这些是"留白"）
- 灾调局高层结构 → 留白
- 多元宇宙的本源 → 留白
- 「门之歌者」「归墟」「零号局长」 → 留白
- 概念融合 / 副本锚点 / 万法归一 → 留白
- 全书反派 → 留白
- 其他女性角色 → 留白

# 输出长度要求
- 总字数控制在 3000-5000 字
- 不要超过 5000 字，立项阶段不需要长文档
- 每节内容精炼，避免堆砌

# 灵感种子（请严格基于此扩展）
{seed}

# 开始输出（直接给出 Markdown，不要前言、不要"好的我来帮您"这种废话）"""


def main():
    seed_path = OUTPUT_DIR / "seed.txt"

    if not seed_path.exists():
        logger.error(f"未找到 seed.txt：{seed_path}，请先在 out_doc 目录下创建该文件")
        return

    seed = seed_path.read_text(encoding="utf-8").strip()
    if not seed:
        logger.error("seed.txt 内容不能为空")
        return

    output_path = get_next_output_path(MD_FILES_DIR, OUTPUT_BASE_NAME, OUTPUT_EXT)
    logger.info(f"本次输出文件：{output_path.name}")

    prompt = build_prompt(seed)

    logger.info("正在调用 LLM 生成世界观（MVP 立项版，聚焦前 10 章）...")
    try:
        response = call_llm(prompt)
    except Exception as e:
        logger.error(f"调用 LLM 失败：{e}", exc_info=True)
        return

    if not response or not response.strip():
        logger.error("LLM 返回内容为空")
        return

    try:
        output_path.write_text(response, encoding="utf-8")
        logger.info(f"世界观生成完成：{output_path}（字数：{len(response)}）")
    except Exception as e:
        logger.error(f"写入文件失败：{e}", exc_info=True)


if __name__ == "__main__":
    main()