# -*- coding: utf-8 -*-
import os
import requests
from local_config import LLM_CONFIG

def get_api_key():
    return os.getenv("LLM_API_KEY", "")

def call_llm(prompt, system_prompt="你是专业网文作者"):
    api_key = get_api_key()
    model = LLM_CONFIG["use_model"]

    if model == "deepseek":
        url = "https://api.deepseek.com/v1/chat/completions"
    elif model == "doubao":
        url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    elif model == "qwen":
        url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": LLM_CONFIG["temperature"],
        "max_tokens": LLM_CONFIG["max_tokens"],
    }

    resp = requests.post(url, json=headers, headers=headers)
    return resp.json()["choices"][0]["message"]["content"]