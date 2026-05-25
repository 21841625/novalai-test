#!/usr/bin/env python3
"""
Unified API client for autonovel.
Supports both Anthropic and DeepSeek API providers.
"""
import os
import sys
import httpx
from pathlib import Path
from dotenv import load_dotenv

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

# API Key - supports both providers
API_KEY = os.environ.get("DEEPSEEK_API_KEY", os.environ.get("ANTHROPIC_API_KEY", ""))
API_BASE_URL = os.environ.get("AUTONOVEL_API_BASE_URL", "https://api.deepseek.com/v1")

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
        raise ValueError("API key not set. Please set DEEPSEEK_API_KEY or ANTHROPIC_API_KEY in .env")
    
    if API_PROVIDER == "anthropic":
        return _call_anthropic(prompt, model, max_tokens, temperature, system)
    else:
        return _call_deepseek(prompt, model, max_tokens, temperature, system)

def _call_anthropic(prompt, model, max_tokens, temperature, system):
    """Call Anthropic Claude API"""
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
    
    resp = httpx.post(
        f"{API_BASE_URL}/v1/messages",
        headers=headers,
        json=payload,
        timeout=600,
    )
    resp.raise_for_status()
    return resp.json()["content"][0]["text"]

def _call_deepseek(prompt, model, max_tokens, temperature, system):
    """Call DeepSeek API (OpenAI compatible)"""
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
    
    resp = httpx.post(
        f"{API_BASE_URL}/chat/completions",
        headers=headers,
        json=payload,
        timeout=600,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

def get_writer_model():
    """Get the configured writer model"""
    return os.environ.get("AUTONOVEL_WRITER_MODEL", "deepseek-v4-flash")

def get_judge_model():
    """Get the configured judge model"""
    return os.environ.get("AUTONOVEL_JUDGE_MODEL", "deepseek-v4-flash")

def get_review_model():
    """Get the configured review model"""
    return os.environ.get("AUTONOVEL_REVIEW_MODEL", "deepseek-v4-pro")

def get_api_key():
    """Get the API key"""
    return API_KEY

def get_api_provider():
    """Get the API provider"""
    return API_PROVIDER
