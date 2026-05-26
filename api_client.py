#!/usr/bin/env python3
"""
Unified API client for autonovel.
Supports both Anthropic and DeepSeek API providers.
"""
import logging
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)

# Windows编码修复
if sys.platform == "win32":
    import io
    # 设置标准输出为UTF-8编码
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

# API Provider configuration
API_PROVIDER = os.environ.get("AUTONOVEL_API_PROVIDER", "deepseek").lower()

# API Key - supports both providers and environment variables directly
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
if not API_KEY:
    API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

API_BASE_URL = os.environ.get("AUTONOVEL_API_BASE_URL", "https://api.deepseek.com/v1")

def validate_api_config():
    """
    验证API配置是否正确。
    检查API密钥和提供程序配置。
    """
    if not API_KEY:
        logger.warning("警告：未找到API密钥。请确保已设置 DEEPSEEK_API_KEY 或 ANTHROPIC_API_KEY 环境变量")
        return False
    
    if API_PROVIDER not in ["anthropic", "deepseek"]:
        logger.warning(f"警告：未知的API提供程序 '{API_PROVIDER}'，将使用 deepseek")
        return False
    
    logger.debug(f"API配置验证通过 - 提供程序: {API_PROVIDER}, 密钥状态: {'已设置' if API_KEY else '未设置'}")
    return True

def call_llm(prompt, model, max_tokens=16000, temperature=0.7, system=None):
    """
    Unified LLM call function that works with both Anthropic and DeepSeek.
    
    Args:
        prompt: User prompt string
        model: Model name
        max_tokens: Maximum tokens to generate
        temperature: Temperature for generation
        system: System prompt (optional)
    
    Returns:
        Generated text response
    """
    if not API_KEY:
        raise ValueError("API key not set. Please set DEEPSEEK_API_KEY or ANTHROPIC_API_KEY in .env or environment variables")
    
    logger.debug(f"调用LLM - 模型: {model}, 温度: {temperature}, 最大令牌: {max_tokens}")
    
    try:
        if API_PROVIDER == "anthropic":
            return _call_anthropic(prompt, model, max_tokens, temperature, system)
        else:
            return _call_deepseek(prompt, model, max_tokens, temperature, system)
    except Exception as e:
        logger.error(f"LLM调用失败: {str(e)}", exc_info=True)
        raise

def _call_anthropic(prompt, model, max_tokens, temperature, system):
    """Call Anthropic Claude API"""
    logger.debug(f"调用 Anthropic API - 模型: {model}")
    
    headers = {
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
        "anthropic-beta": "context-1m-2025-08-07",
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        payload["system"] = system
    
    try:
        resp = httpx.post(
            f"{API_BASE_URL}/v1/messages",
            headers=headers,
            json=payload,
            timeout=600,
        )
        resp.raise_for_status()
        result = resp.json()["content"][0]["text"]
        logger.debug(f"Anthropic API调用成功，响应长度: {len(result)} 字符")
        return result
    except httpx.TimeoutException:
        logger.error("Anthropic API调用超时")
        raise
    except httpx.HTTPStatusError as e:
        logger.error(f"Anthropic API HTTP错误: {e.response.status_code} - {e.response.text}")
        raise
    except KeyError as e:
        logger.error(f"Anthropic API响应解析错误: {e}")
        raise
    except Exception as e:
        logger.error(f"Anthropic API调用异常: {str(e)}", exc_info=True)
        raise

def _call_deepseek(prompt, model, max_tokens, temperature, system):
    """Call DeepSeek API (OpenAI compatible)"""
    logger.debug(f"调用 DeepSeek API - 模型: {model}, 基础URL: {API_BASE_URL}")
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        payload["messages"].insert(0, {"role": "system", "content": system})
    
    try:
        resp = httpx.post(
            f"{API_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=600,
        )
        resp.raise_for_status()
        result = resp.json()["choices"][0]["message"]["content"]
        logger.debug(f"DeepSeek API调用成功，响应长度: {len(result)} 字符")
        return result
    except httpx.TimeoutException:
        logger.error("DeepSeek API调用超时")
        raise
    except httpx.HTTPStatusError as e:
        error_msg = f"DeepSeek API HTTP错误: {e.response.status_code}"
        try:
            error_detail = e.response.json()
            if "error" in error_detail:
                error_msg += f" - {error_detail['error'].get('message', '未知错误')}"
        except:
            pass
        logger.error(error_msg)
        raise
    except KeyError as e:
        logger.error(f"DeepSeek API响应解析错误: {e}")
        raise
    except Exception as e:
        logger.error(f"DeepSeek API调用异常: {str(e)}", exc_info=True)
        raise

def get_writer_model():
    """Get the configured writer model"""
    model = os.environ.get("AUTONOVEL_WRITER_MODEL", "deepseek-v4-flash")
    logger.debug(f"获取写作模型: {model}")
    return model

def get_judge_model():
    """Get the configured judge model"""
    model = os.environ.get("AUTONOVEL_JUDGE_MODEL", "deepseek-v4-flash")
    logger.debug(f"获取评判模型: {model}")
    return model

def get_review_model():
    """Get the configured review model"""
    model = os.environ.get("AUTONOVEL_REVIEW_MODEL", "deepseek-v4-pro")
    logger.debug(f"获取审查模型: {model}")
    return model

def get_api_key():
    """Get the API key"""
    return API_KEY

def get_api_provider():
    """Get the API provider"""
    return API_PROVIDER