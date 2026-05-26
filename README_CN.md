# autonovel - AI自动小说生成管道

一个自动化管道，用于创作、修改、排版、插图和叙述完整的小说。从一个种子概念到可打印的PDF、ePub、有声读物和落地页——全部由AI代理生成。

灵感来源于 [karpathy/autoresearch](https://github.com/karpathy/autoresearch)：将相同的"修改-评估-保留/舍弃"循环应用于小说创作。

**第一部产出的小说：** *《钟声之家的次子》(The Second Son of the House of Bells)* ——
19章，79,456字。
查看 `autonovel/bells` 分支。

---

## 快速开始

```bash
# 克隆项目并设置
git clone <repo-url> && cd autonovel
cp .env.example .env    # 添加你的API密钥

# 安装依赖
uv sync

# 生成种子概念（或在seed.txt中编写自己的）
uv run python seed.py

# 运行完整管道
uv run python run_pipeline.py --from-scratch
```

---

## 管道流程

### 阶段1：基础构建 (Foundation)
从种子概念构建世界、角色、大纲、文风声音和典章。
循环直到 `foundation_score > 7.5`。

### 阶段2：初稿 (First Draft)
按顺序撰写章节。评估每一章。如果 `score > 6.0` 则保留，
否则重试。进度优先于完美。

### 阶段3a：自动修改 (Automated Revision)
对抗性编辑 → 应用删减 → 读者评审团 → 生成修改摘要 →
重写章节。当分数稳定时，平台检测会停止循环。

### 阶段3b：Opus审查循环 (Opus Review Loop)
将完整手稿发送给Claude Opus进行双角色审查
（文学评论家 + 小说教授）。解析可操作的建议项。
修复顶级问题。重复直到评审者没有主要问题。

### 阶段4：导出 (Export)
重建文档、LaTeX排版、生成插图、制作有声读物脚本、
构建ePub、创建落地页。

完整技术规范请参阅 [PIPELINE.md](PIPELINE.md)。

---

## 工具列表（27个Python脚本）

### 基础构建 (Foundation)
| 工具 | 用途 |
|------|------|
| `seed.py` | 生成种子概念 |
| `gen_world.py` | 种子 → 世界设定圣经 |
| `gen_characters.py` | 种子 + 世界 → 角色注册表 |
| `gen_outline.py` | 带有节拍和伏笔的大纲 |
| `gen_outline_part2.py` | 伏笔记录 |
| `gen_canon.py` | 硬事实交叉引用 |
| `voice_fingerprint.py` | 文风分析与发现 |

### 草稿撰写 (Drafting)
| 工具 | 用途 |
|------|------|
| `draft_chapter.py` | 按照反模式规则撰写单章 |
| `run_drafts.py` | 批量顺序章节撰写 |

### 评估 (Evaluation)
| 工具 | 用途 |
|------|------|
| `evaluate.py` | 机械AI痕迹评分器 + LLM评判 |
| `adversarial_edit.py` | "删减500字"分析 → 分类删减 |
| `compare_chapters.py` | 一对一Elo锦标赛 |
| `reader_panel.py` | 四角色小说级别评估 |
| `review.py` | Opus双角色审查（含停止条件） |

### 修改 (Revision)
| 工具 | 用途 |
|------|------|
| `gen_brief.py` | 从反馈自动生成修改摘要 |
| `gen_revision.py` | 根据修改摘要重写章节 |
| `apply_cuts.py` | 批量应用对抗性删减 |

### 插图与封面 (Art & Cover)
| 工具 | 用途 |
|------|------|
| `gen_art.py` | 插图管道：风格、精选、装饰、矢量化 |
| `gen_art_directions.py` | 生成多样的插图方向供筛选 |
| `gen_cover_composite.py` | 封面插图文字叠加 |
| `gen_cover_print.py` | 可打印全包裹封面（Lulu/KDP规格） |

### 有声读物 (Audiobook)
| 工具 | 用途 |
|------|------|
| `gen_audiobook_script.py` | 将章节解析为带说话者属性的脚本 |
| `gen_audiobook.py` | 通过ElevenLabs生成多声音频 |

### 编排 (Orchestration)
| 工具 | 用途 |
|------|------|
| `run_pipeline.py` | 完整管道编排器（种子 → 完成小说） |
| `build_arc_summary.py` | 从章节重新生成弧线摘要 |
| `build_outline.py` | 从章节重新生成大纲 |

---

## 文件结构

```
框架部分（可复用，在master分支）：
  program.md             — 各阶段的代理指令
  CRAFT.md               — 写作技巧教育（情节、角色、世界、散文）
  ANTI-SLOP.md           — 词汇级AI痕迹检测
  ANTI-PATTERNS.md       — 结构级AI模式检测
  PIPELINE.md            — 完整自动化规范
  WORKFLOW.md            — 分步人工指南

模板部分（每部小说在分支上填充）：
  voice.md               — 第一部分：护栏规则；第二部分：每部小说发现的文风
  world.md               — 世界设定圣经模板
  characters.md          — 角色注册表模板
  outline.md             — 章节大纲模板
  canon.md               — 硬事实数据库
  MYSTERY.md             — 核心谜团（仅作者可见）
  state.json             — 管道状态追踪器

排版部分：
  typeset/novel.tex      — LaTeX模板（EB Garamond字体，平装书）
  typeset/build_tex.py   — 章节 → 带矢量装饰的LaTeX
  typeset/epub_*          — ePub元数据、CSS和前置内容

插图部分：
  audiobook_voices.json  — 角色 → ElevenLabs声音映射
  landing/index.html     — 响应式落地页模板

配置部分：
  .env.example           — API密钥（Anthropic、fal.ai、ElevenLabs）
  pyproject.toml         — Python依赖
```

---

## 工作原理

小说由五个共同进化的层次组成：

```
  第5层:  voice.md          — 我们如何写作 (HOW)
  第4层:  world.md          — 存在什么 (WHAT)
  第3层:  characters.md     — 谁在行动 (WHO)
  第2层:  outline.md        — 发生了什么 (WHAT HAPPENS)
  第1层:  chapters/ch_NN.md — 实际散文内容 (THE ACTUAL PROSE)
  贯穿层: canon.md         — 什么是真实的 (WHAT IS TRUE)
```

变更会双向传播（设定变更 → 大纲变更 → 章节修改）
和向上传播（写作揭示漏洞 → 更新设定 → 检查下游）。管道在 `state.json` 中追踪传播债务。

### 两个免疫系统

1. **机械检测** (`evaluate.py`，无需LLM)：正则扫描禁用词汇、
   小说陈词滥调、"展示而非讲述"违规、句子统一性问题。

2. **LLM评判** (`evaluate.py`，独立模型)：评分散文质量、
   文风一致性、角色独特性、节拍覆盖度。

### Opus审查循环

经过自动修改循环后，完整手稿会发送给Claude Opus，附带以下提示：

> "阅读下面的小说。首先作为文学评论家，然后作为小说教授进行审查。
> 针对发现的任何缺陷给出具体、可操作的建议。要公平但诚实。不必刻意找缺陷。"

双角色审查能捕捉自动工具无法发现的问题：散文级重复、角色单薄、伦理漏洞、结构单调。
循环持续直到评审者的建议大多是有条件的保留意见而非真正的问题。

---

## API密钥

管道使用三个外部服务：

| 服务 | 密钥 | 用途 |
|------|------|------|
| Anthropic | `ANTHROPIC_API_KEY` | 写作、评估、审查（Sonnet + Opus） |
| fal.ai | `FAL_KEY` | 封面插图和装饰生成（Nano Banana 2） |
| ElevenLabs | `ELEVENLABS_API_KEY` | 多声有声读物生成 |

复制 `.env.example` 到 `.env` 并填写密钥。核心管道只需要 Anthropic 密钥。
插图和有声读物是可选的。

---

## 制作历史

第一部小说《钟声之家的次子》(The Second Son of the House of Bells) 通过此管道制作：

- **基础构建:** 世界圣经、8个角色、24章大纲、文风发现
- **草稿:** 24章，75,698字，顺序撰写并评估
- **修改:** 6轮自动循环 + 6轮Opus审查
- **结构:** 通过4次合并从24章精简到19章
- **插图:** Linocut封面（Nano Banana 2）、19个木刻章节装饰（矢量化）
- **有声读物:** 19章解析为4,179个带说话者属性的片段
- **最终:** 79,456字，6轮审查，所有主要问题已解决

---

## 灵感来源

- [karpathy/autoresearch](https://github.com/karpathy/autoresearch) — 自主研究循环
- Brandon Sanderson的写作讲座（魔法定律、角色滑块）
- K.M. Weiland的《Creating Character Arcs》
- Blake Snyder的《Save the Cat》
- Ursula K. Le Guin的《From Elfland to Poughkeepsie》
- [slop-forensics](https://github.com/sam-paech/slop-forensics) 和 [EQ-Bench Slop Score](https://eqbench.com/slop-score.html)