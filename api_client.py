# -*- coding: utf-8 -*-
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

from local_config import LLM_CONFIG

# 加载 .env 配置文件
BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

# 不同模型对应的环境变量名映射
MODEL_API_KEY_ENV = {
    "deepseek": "DEEPSEEK_API_KEY",
    "doubao": "DOUBAO_API_KEY",
    "huoshan": "VOLCANO_API_KEY",
    "qwen": "DASHSCOPE_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}

# 不同 provider 对应的 API endpoint（fallback 默认值，优先从 .env 读取）
DEFAULT_API_URL = {
    "deepseek": "https://api.deepseek.com/v1",
    "doubao": "https://ark.cn-beijing.volces.com/api/v3",
    "huoshan": "https://ark.cn-beijing.volces.com/api/v3",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "anthropic": "https://api.anthropic.com",
}

# 不同 provider 对应的真实模型名（fallback 默认值，优先从 .env 读取 AUTONOVEL_WRITER_MODEL）
DEFAULT_MODEL_NAME = {
    "deepseek": "deepseek-v4-flash",
    "doubao": "doubao-1-5-pro-32k-250115",
    "huoshan": "doubao-1-5-pro-32k-250115",
    "qwen": "qwen-plus",
    "anthropic": "claude-sonnet-4-6",
}

def get_api_key(model: str = None):
    """
    根据传入的模型名称读取对应的 API Key 环境变量。
    若未传入 model 参数，则优先读取 .env 中的 AUTONOVEL_API_PROVIDER，
    否则从 LLM_CONFIG["use_model"] 中读取当前使用的模型。

    参数：
        model: 模型名称（deepseek / doubao / huoshan / qwen / anthropic），可选
    返回：
        对应模型的 API Key 字符串
    """
    if model is None:
        model = os.getenv("AUTONOVEL_API_PROVIDER") or LLM_CONFIG["use_model"]
    env_name = MODEL_API_KEY_ENV.get(model, "DEEPSEEK_API_KEY")
    return os.getenv(env_name, "")

def get_writer_model():
    """从 .env 读取写作模型名，缺省时回退到默认映射"""
    provider = os.getenv("AUTONOVEL_API_PROVIDER") or LLM_CONFIG["use_model"]
    return os.getenv("AUTONOVEL_WRITER_MODEL") or DEFAULT_MODEL_NAME.get(provider, provider)

def get_judge_model():
    """从 .env 读取评审模型名，缺省时回退到写作模型"""
    return os.getenv("AUTONOVEL_JUDGE_MODEL") or get_writer_model()

def get_review_model():
    """从 .env 读取审查模型名，缺省时回退到写作模型"""
    return os.getenv("AUTONOVEL_REVIEW_MODEL") or get_writer_model()

def get_main_model():
    """主模型（兼容旧接口），等同于写作模型"""
    return get_writer_model()

def call_llm(prompt, system_prompt="你是专业网文作者"):
    # 优先使用 .env 中的 AUTONOVEL_API_PROVIDER，否则使用 local_config 中的 use_model
    provider = os.getenv("AUTONOVEL_API_PROVIDER") or LLM_CONFIG["use_model"]
    api_key = get_api_key(provider)

    if not api_key:
        raise ValueError(
            f"未找到 {provider} 的 API Key，请在 .env 中设置 "
            f"{MODEL_API_KEY_ENV.get(provider, 'DEEPSEEK_API_KEY')}"
        )

    # 优先使用 .env 中配置的 AUTONOVEL_API_BASE_URL，否则使用默认 URL
    base_url = os.getenv("AUTONOVEL_API_BASE_URL") or DEFAULT_API_URL.get(provider)
    if not base_url:
        raise ValueError(f"未支持的模型 provider: {provider}")
    url = f"{base_url.rstrip('/')}/chat/completions"

    # 优先使用 .env 中的 AUTONOVEL_WRITER_MODEL，再次是 LLM_CONFIG.model_name，最后是默认映射
    real_model = (
        os.getenv("AUTONOVEL_WRITER_MODEL")
        or LLM_CONFIG.get("model_name")
        or DEFAULT_MODEL_NAME.get(provider, provider)
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    data = {
        "model": real_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": LLM_CONFIG["temperature"],
        "max_tokens": LLM_CONFIG["max_tokens"],
    }

    try:
        resp = requests.post(url, json=data, headers=headers, timeout=600)
        resp.raise_for_status()
    except requests.exceptions.HTTPError as e:
        # 输出 API 返回的具体错误信息，便于排查
        err_body = ""
        try:
            err_body = resp.text
        except Exception:
            pass
        raise RuntimeError(
            f"[{provider}] API 调用失败 HTTP {resp.status_code}：{err_body}"
        ) from e
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"[{provider}] 请求异常：{e}") from e

    try:
        result = resp.json()
    except ValueError as e:
        raise RuntimeError(f"[{provider}] 响应解析失败：{resp.text}") from e

    if "choices" not in result:
        raise RuntimeError(f"[{provider}] 响应中无 choices 字段，原始响应：{result}")

    return result["choices"][0]["message"]["content"]