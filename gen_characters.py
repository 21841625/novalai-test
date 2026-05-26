#!/usr/bin/env python3
"""
角色注册表生成器 - 为基础阶段生成 角色设定.md 文件。
读取 seed.txt + voice.md + 世界设定.md + CRAFT.md，调用写作模型生成角色设定。
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
    调用写作模型生成角色设定内容。
    
    参数：
        prompt: 提示词字符串
        max_tokens: 生成的最大令牌数（默认16000）
    
    返回：
        生成的角色注册表文本
    """
    system_prompt = (
        "你是一位专业的小说角色设计师，精通创伤/欲望/需求/谎言框架、桑德森的三个滑块理论和对话独特性。"
        "你创造的角色感觉像真实的人，有矛盾、秘密和可识别的说话模式。"
        "你从不使用陈词滥调词汇。请用中文写作，风格简洁直接。"
    )
    return call_llm(prompt, WRITER_MODEL, max_tokens, temperature=0.7, system=system_prompt)

# 确保目录存在
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MD_FILES_DIR.mkdir(parents=True, exist_ok=True)

# 文件路径
SEED_FILE = OUTPUT_DIR / "seed.txt"
VOICE_FILE = BASE_DIR / "voice.md"
WORLD_FILE = MD_FILES_DIR / "世界设定.md"
OUTPUT_FILE = MD_FILES_DIR / "角色设定.md"

# 验证API配置
validate_api_config()

if not API_KEY:
    logger.error(f"错误：请先在 .env 中设置 {'DEEPSEEK_API_KEY' if API_PROVIDER == 'deepseek' else 'ANTHROPIC_API_KEY'}")
    sys.exit(1)

# 检查必要文件
if not SEED_FILE.exists():
    logger.error(f"错误：未找到种子文件 {SEED_FILE}")
    sys.exit(1)

if not VOICE_FILE.exists():
    logger.error(f"错误：未找到语音文件 {VOICE_FILE}")
    sys.exit(1)

if not WORLD_FILE.exists():
    logger.error(f"错误：未找到世界设定文件 {WORLD_FILE}")
    logger.error("请先运行 gen_world.py 生成世界设定")
    sys.exit(1)

logger.info(f"加载种子文件: {SEED_FILE}")
seed = SEED_FILE.read_text(encoding='utf-8')

logger.info(f"加载世界设定文件: {WORLD_FILE}")
world = WORLD_FILE.read_text(encoding='utf-8')

logger.info(f"加载语音文件: {VOICE_FILE}")
voice = VOICE_FILE.read_text(encoding='utf-8')

# Voice Part 2 only
voice_lines = voice.split('\n')
part2_start = next(i for i, l in enumerate(voice_lines) if 'Part 2' in l or '第二部分' in l)
voice_part2 = '\n'.join(voice_lines[part2_start:])

prompt = f"""为这部小说构建完整的角色注册表。这是 角色设定.md ——
关于故事中存在谁、什么驱动他们、他们如何说话以及他们背负什么秘密的权威参考。

种子概念：
{seed}

世界圣经（这些角色所处的世界）：
{world}

语音特征（小说的基调）：
{voice_part2}

角色塑造要求：

### 三个滑块（桑德森）
每个角色有三个独立的刻度（0-10）：
  主动性 -- 他们是推动剧情还是被动反应？
  亲和力 -- 读者是否同情他们？
  能力 -- 他们是否擅长自己做的事？
规则：引人入胜 = 至少两项高，或一项高且有明显成长。

### 创伤/欲望/需求/谎言框架
一个因果链：
  幽灵（背景事件）-> 创伤（持续的伤害）-> 谎言（用来应对的错误信念）
    -> 欲望（由谎言驱动的外部目标）-> 需求（内部真相，与谎言对立）
规则：欲望和需求必须处于张力中。谎言可以用一句话陈述。
  真相是其直接对立面。

### 对话独特性（8个维度）
1. 词汇水平  2. 句子长度  3. 缩略语/正式程度
4. 言语习惯  5. 提问与陈述比例  6. 打断模式
7. 比喻领域  8. 直接与间接
测试：移除对话标签。你能分辨是谁在说话吗？

构建角色注册表，包含至少6-8个角色：

1. **主角**（POV角色）
   - 完整的创伤/欲望/需求/谎言链
   - 三个滑块及理由
   - 弧线类型（正/负/平）
   - 详细的说话模式（8个维度）
   - 身体习惯和不自觉的小动作
   - 至少2个秘密
   - 关键关系映射

2. **主要对手/反派**
   - 不是纯粹的恶人——而是利益与主角冲突的人
   - 他/她自己的创伤/欲望/需求/谎言（应该可以理解）

3. **配角1**（家人/朋友/导师）
   - 与主角同样深度
   - 他/她的秘密和隐藏的动机

4. **配角2**（盟友/同伴）
   - 即使他大部分故事中缺席，也需要完整深度
   - 通过行动或缺席体现的存在感

5. **制度性对手**（组织/系统的化身）
   - 他/她相信自己在做正确的事

6. **至少1-2个故事需要的额外角色**
   - 根据故事类型添加合适的角色

每个角色包括：
- 姓名、年龄、角色定位
- 幽灵/创伤/欲望/需求/谎言链（主要角色）
- 三个滑块（主动性/亲和力/能力）带数字和理由
- 弧线类型和轨迹
- 说话模式（所有8个维度，带示例台词）
- 外貌（具体，不俗套）
- 身体习惯和不自觉的小动作
- 秘密（读者不会立即知道的）
- 关键关系（映射到其他角色）
- 主题角色（这个角色体现什么问题？）

重要提示：
- 角色必须相互关联。他们的欲望应该相互冲突。
- 每个秘密都应该是如果揭示会改变故事的东西。
- 说话模式必须足够独特以通过无标签测试。
- 目标约3000-4000字。密集的角色塑造，不要冗余。
请用中文输出。
"""

logger.info(f"正在调用写作模型生成角色设定...")
try:
    result = call_writer(prompt)
    
    logger.info(f"保存角色设定到: {OUTPUT_FILE}")
    OUTPUT_FILE.write_text(result, encoding='utf-8')
    logger.info(f"角色设定生成完成，字数: {len(result)}")
    
    print(result)
except Exception as e:
    logger.error(f"生成角色设定时发生错误: {str(e)}", exc_info=True)
    sys.exit(1)