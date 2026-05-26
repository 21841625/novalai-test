#!/usr/bin/env python3
"""
世界设定生成器 - 为中文小说定制的世界设定.md 文件生成工具。
适配中国本土小说风格：仙侠/武侠/都市/历史/玄幻/古风等，读取 seed.txt + voice.md + CRAFT.md 生成符合国内创作习惯的世界设定。
"""
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List

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

# 中文小说类型映射及侧重点配置
NOVEL_TYPE_CONFIG: Dict[str, Dict[str, str]] = {
    "仙侠": {
        "focus": "修真体系、境界划分、宗门设定、天地法则、灵根资质、法宝丹药、天劫轮回、仙凡之别",
        "special_system": "修真体系（境界/功法/法术）、灵根/体质、丹药/炼器/符箓/阵法、洞天福地、天劫规则",
        "geography": "三界六道、洞天福地、险地秘境、宗门驻地、凡间王朝、洪荒九州",
        "faction": "宗门（正邪）、散修联盟、妖族势力、天庭/地府、凡间王朝、上古神族/魔族"
    },
    "武侠": {
        "focus": "武功秘籍、门派设定、江湖格局、武学境界、兵器谱、侠义精神、朝廷与江湖",
        "special_system": "武学体系（内功/外功）、经脉穴位、轻功身法、毒术医术、武功境界划分",
        "geography": "江湖门派驻地、武林秘境、朝廷疆域、茶马古道、江南水乡、塞北荒漠",
        "faction": "名门正派、邪派魔教、朝廷势力、江湖世家、隐世宗门、丐帮/商会等江湖组织"
    },
    "都市": {
        "focus": "现代都市背景、异能/重生/系统、社会阶层、职业设定、都市传说、地域特色（北上广深/小城）",
        "special_system": "异能体系/重生金手指/系统规则、代价与限制、觉醒条件、能力等级",
        "geography": "一线城市/二线小城、标志性建筑、隐藏据点、灰色地带、特色街区",
        "faction": "官方特殊机构、地下势力、商业巨头、异能者组织、普通社会阶层、神秘家族"
    },
    "历史": {
        "focus": "朝代考据、社会制度、历史事件改编、人物符合时代特征、地域文化特色",
        "special_system": "古代科技/权谋规则/武学（若有）、官场体系、战争规则、经济制度",
        "geography": "符合朝代的疆域、都城/重镇、关隘要塞、运河驿站、边疆部落领地",
        "faction": "朝堂派系、地方豪强、文人集团、军阀门阀、江湖势力（若有）、外族势力"
    },
    "玄幻": {
        "focus": "境界体系、血脉设定、天地规则、种族设定、宗门帝国、法宝神器、修炼资源",
        "special_system": "修炼境界、血脉天赋、武魂/灵宠、斗技/魔法、炼体/炼魂、位面规则",
        "geography": "各大洲域、禁地秘境、宗门疆域、帝国版图、异位面/小世界",
        "faction": "人族帝国、宗门联盟、异族部落（妖/魔/鬼/兽）、上古遗族、佣兵团/商会"
    },
    "古风言情": {
        "focus": "朝代背景、社会礼制、世家格局、情感线设定、服饰礼仪、地域文化、宫廷规则",
        "special_system": "权谋规则、才情技艺（琴棋书画）、家族势力运作、宫廷晋升体系",
        "geography": "京城/江南/塞北、世家府邸、宫廷布局、别院行宫、特色城镇",
        "faction": "后宫派系、朝堂世家、文人团体、地方藩王、江湖暗线（若有）"
    }
}

def detect_novel_type(seed_text: str) -> str:
    """
    从种子文本中自动检测小说类型
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
    
    type_scores = {novel_type: 0 for novel_type in NOVEL_TYPE_CONFIG.keys()}
    for novel_type, keywords in type_keywords.items():
        for keyword in keywords:
            if keyword in seed_lower:
                type_scores[novel_type] += 1
    
    # 返回得分最高的类型，默认返回都市
    return max(type_scores, key=type_scores.get) if max(type_scores.values()) > 0 else "都市"

def call_writer(prompt: str, novel_type: str, max_tokens: int = 20000) -> str:
    """
    调用写作模型生成适配中文小说风格的世界设定内容。
    
    参数：
        prompt: 提示词字符串
        novel_type: 小说类型（仙侠/武侠/都市/历史/玄幻/古风言情）
        max_tokens: 生成的最大令牌数（默认20000，适配更长的中文内容）
    
    返回：
        生成的世界设定文本
    """
    # 针对中文小说风格的系统提示
    system_prompt = f"""
你是一位精通中国本土小说创作的专业世界构建师，擅长仙侠、武侠、都市、历史、玄幻、古风言情等多种中文小说风格。
你的世界设定需要符合以下要求：
1. 符合国内读者的阅读习惯和审美偏好，细节具体、体系完整、逻辑自洽
2. 仙侠/武侠注重境界划分、宗门设定、功法体系的合理性和层次感
3. 都市类贴近中国现实社会，地域特色鲜明（如北上广深、新一线、小县城等）
4. 历史类尊重基本历史框架，同时允许合理改编，符合对应朝代的社会特征
5. 玄幻类注重体系创新，避免同质化，设定有记忆点的核心规则
6. 古风言情注重礼制、服饰、社交规则的细节，符合时代背景

写作风格要求：
- 语言风格：简洁流畅的中文，符合网文创作习惯，避免欧化句式
- 细节要求：有具体的名称、数值、规则，可直接用于小说写作
- 体系设计：层次分明，有明确的升级路径和限制条件
- 文化内核：体现中国传统文化元素（如儒释道、阴阳五行、天干地支等）
- 冲突设计：为后续剧情埋下足够的矛盾点和爽点

当前创作类型：{novel_type}，重点关注：{NOVEL_TYPE_CONFIG[novel_type]['focus']}
"""
    return call_llm(prompt, WRITER_MODEL, max_tokens, temperature=0.75, system=system_prompt)

def generate_china_style_prompt(seed: str, voice_part2: str, craft: str, novel_type: str) -> str:
    """
    生成适配中文小说风格的提示词
    """
    type_config = NOVEL_TYPE_CONFIG[novel_type]
    
    prompt = f"""
为这部{novel_type}小说构建完整的世界设定圣经（世界设定.md），作为故事创作的权威参考文档。

【核心设定】
种子概念：
{seed}

【风格基调】
语音特征（小说的基调）：
{voice_part2}

【世界构建核心要求】
{craft}

【{novel_type}类型专项要求】
1. 核心体系：{type_config['special_system']}
   - 体系需有明确的等级/境界划分，每个等级有具体的能力和限制
   - 能力使用需有代价（如灵气消耗、修为倒退、心魔反噬、天谴等）
   - 体系需内部一致，符合{novel_type}的核心逻辑

2. 地理设定：{type_config['geography']}
   - 至少8个有具体名称和功能的核心地点
   - 地点需有感官细节（视觉、听觉、嗅觉、触觉）
   - 地理环境需与剧情和修炼/生存体系相匹配

3. 势力设定：{type_config['faction']}
   - 至少6个核心势力，包含对立/合作关系
   - 每个势力有明确的目标、组织结构、核心人物特征
   - 势力间的利益冲突需清晰，能支撑主要剧情线

【世界设定文档结构（适配中文小说创作）】
请严格按照以下章节构建，总字数控制在5000-8000字：

1. **核心设定总览**
   - 世界名称：符合{novel_type}风格的正式名称+别称
   - 一句话核心简介：提炼最具特色的设定亮点
   - 小说类型定位：明确风格（如：古典仙侠/现代都市异能/架空历史权谋）
   - 核心爽点/主题：故事想要表达的核心冲突和看点

2. **时空与地理设定**
   - 世界版图：整体格局描述（如：三界九州/现代华夏/架空大靖王朝）
   - 核心地点（至少8个）：
     - 名称+定位（如：青云宗-正道三大宗门之一）
     - 地理特征（地形、气候、环境）
     - 功能定位（修炼圣地/权力中心/贸易枢纽/险地秘境）
     - 感官细节（气味：终年弥漫檀香与丹药气息；声音：晨钟暮鼓伴随弟子诵经声）
   - 时间体系：
     - 纪年方式（如：修真历/王朝年号/公元纪年）
     - 关键时间节点（创世/大战/变革事件）
     - 时间流速规则（如：洞天内一日，外界一年）

3. **核心力量体系**
   - 体系名称与核心逻辑（如：玄天修真体系/龙虎武学体系/都市异能觉醒体系）
   - 等级/境界划分（从入门到顶级，至少8个等级）：
     | 等级名称 | 核心能力 | 修炼条件 | 进阶代价 | 标志性特征 |
     |----------|----------|----------|----------|------------|
     | 炼气期   | 引气入体 | 灵根资质 | 无       | 可御使基础法术 |
   - 能力使用规则：
     - 启动条件（如：特定心法/道具/血脉）
     - 消耗/代价（如：灵气/气血/寿元/精神力）
     - 限制/禁忌（如：不可对凡人使用/每月限用3次/需特定时辰）
   - 辅助体系：{type_config['special_system'].split('、')[1:] if len(type_config['special_system'].split('、'))>1 else '配套的辅助能力体系'}

4. **势力与权力结构**
   - 势力图谱：核心势力的关系网络（敌对/同盟/竞争/依附）
   - 主要势力（至少6个）：
     - 势力名称+定位
     - 核心目标与价值观
     - 组织结构（如：宗主-长老-核心弟子-外门弟子）
     - 核心资源/优势
     - 弱点/隐患
     - 代表人物（简要设定）
   - 权力运作规则：
     - 核心权力来源（如：实力/血脉/官位/财富）
     - 制衡机制
     - 隐藏势力/幕后黑手

5. **社会与文化设定**
   - 阶层划分：
     - 各阶层的地位、权利、生存状态
     - 阶层流动规则（如：通过修炼/科举/战功晋升）
   - 核心文化习俗：
     - 节日庆典（如：宗门开山节/王朝祭天礼/都市异能者地下集会）
     - 礼仪规范（如：师徒之礼/朝堂跪拜/江湖抱拳礼）
     - 禁忌与规矩（如：不可越级挑战/后宫不得干政/异能者不可暴露身份）
   - 价值观与道德观：
     - 主流价值观（如：侠之大者为国为民/实力至上/家族利益优先）
     - 冲突的价值观（为后续剧情埋下伏笔）
   - 经济与资源体系：
     - 核心资源（如：灵石/银两/异能结晶/粮食）
     - 流通规则（如：坊市交易/官方专卖/地下黑市）
     - 贫富差距与影响

6. **历史与关键事件**
   - 时间线（至少5个关键节点）：
     | 时间 | 事件名称 | 事件内容 | 对现在的影响 |
     |------|----------|----------|--------------|
     | 300年前 | 仙魔大战 | 正道联合对抗魔族入侵 | 形成现在的宗门格局，遗留多处战场秘境 |
   - 未解之谜/历史伏笔：
     - 至少3个待解开的秘密（如：上古魔神封印松动/前朝宝藏下落/主角身世之谜）
   - 历史遗留问题：
     - 未解决的冲突（如：宗门间的旧怨/民族矛盾/阶级对立）

7. **核心冲突与剧情钩子**
   - 主线冲突：故事的核心矛盾（如：正邪之争/皇权争夺/异能者暴露危机）
   - 支线冲突：辅助的次要矛盾（如：师门内斗/家族恩怨/资源争夺）
   - 剧情钩子（至少5个）：
     - 可直接使用的剧情起点/转折点
     - 包含悬念和爽点设计
   - 主角成长路径：
     - 核心挑战
     - 成长代价
     - 关键突破点

8. **创作注意事项**
   - 避坑指南：避免的俗套设定（如：无脑开挂/逻辑漏洞/人设崩塌）
   - 特色强化：重点突出的设定亮点
   - 改编空间：可扩展/调整的设定方向

【重要创作规则】
1. 所有设定需服务于剧情，避免无意义的堆砌
2. 数值/等级设定需具体，可直接用于写作
3. 融入中国传统文化元素（阴阳五行、天干地支、儒释道思想、传统节日等）
4. 避免西化设定，保持中式审美和思维方式
5. 每个设定都需考虑"代价"和"限制"，冲突才更有张力
6. 语言风格：使用流畅的中文网文风格，避免翻译腔和生硬的句式
7. 细节要有画面感，能让读者直观感受到世界的真实感

请严格按照以上要求创作，输出完整的世界设定文档，使用中文，格式清晰，可直接保存为Markdown文件。
"""
    return prompt

# 确保目录存在
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MD_FILES_DIR.mkdir(parents=True, exist_ok=True)

# 文件路径
SEED_FILE = OUTPUT_DIR / "seed.txt"
VOICE_FILE = BASE_DIR / "voice.md"
CRAFT_FILE = BASE_DIR / "CRAFT.md"
OUTPUT_FILE = MD_FILES_DIR / "世界设定.md"

def main():
    """主函数"""
    # 验证API配置
    validate_api_config()

    if not API_KEY:
        logger.error(f"错误：请先在 .env 中设置 {'DEEPSEEK_API_KEY' if API_PROVIDER == 'deepseek' else 'ANTHROPIC_API_KEY'}")
        sys.exit(1)

    # 检查必要文件
    required_files = [
        (SEED_FILE, "种子文件"),
        (VOICE_FILE, "语音文件"),
        (CRAFT_FILE, "写作技巧文件")
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

    # 提取voice的第二部分
    voice_lines = voice.split('\n')
    try:
        part2_start = next(i for i, l in enumerate(voice_lines) if 'Part 2' in l or '第二部分' in l)
        voice_part2 = '\n'.join(voice_lines[part2_start:])
    except StopIteration:
        logger.warning("未找到Part 2/第二部分标记，使用完整语音文件内容")
        voice_part2 = voice

    # 自动检测小说类型
    novel_type = detect_novel_type(seed)
    logger.info(f"自动检测到小说类型：{novel_type}")

    # 生成定制化提示词
    prompt = generate_china_style_prompt(seed, voice_part2, craft, novel_type)

    # 调用模型生成内容
    logger.info(f"正在调用写作模型生成{novel_type}风格的世界设定...")
    try:
        result = call_writer(prompt, novel_type)
        
        # 保存结果
        logger.info(f"保存世界设定到: {OUTPUT_FILE}")
        OUTPUT_FILE.write_text(result, encoding='utf-8')
        logger.info(f"世界设定生成完成，字数: {len(result)}")
        
        print(f"\n===== {novel_type}风格世界设定生成完成 =====")
        print(result)
        
    except Exception as e:
        logger.error(f"生成世界设定时发生错误: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()