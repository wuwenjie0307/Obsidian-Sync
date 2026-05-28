"""
调用硅基流动 (SiliconFlow) 视觉模型识别图片内容。

用法:
    python vision.py <图片路径> [提示词]

环境变量:
    SILICONFLOW_API_KEY — 硅基流动 API 密钥（必填）
    SILICONFLOW_MODEL   — 模型名（可选，默认 Qwen/Qwen3.6-35B-A3B）
"""

import base64
import json
import os
import sys

import requests

API_BASE = "https://api.siliconflow.cn/v1"
DEFAULT_MODEL = "Qwen/Qwen3.6-35B-A3B"
DEFAULT_PROMPT = "请详细描述这张图片的内容，包括画面中的主体、场景、文字、颜色、布局等所有可见信息。"


def encode_image(file_path: str) -> str:
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def get_mime_type(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
    }
    return mime_map.get(ext, "image/png")


def call_vision_api(image_path: str, prompt: str = None) -> dict:
    api_key = os.environ.get("SILICONFLOW_API_KEY", "")
    if not api_key:
        return {"error": "未设置 SILICONFLOW_API_KEY 环境变量"}

    model = os.environ.get("SILICONFLOW_MODEL", DEFAULT_MODEL)
    prompt = prompt or DEFAULT_PROMPT

    if not os.path.isfile(image_path):
        return {"error": f"图片文件不存在: {image_path}"}

    mime = get_mime_type(image_path)
    b64 = encode_image(image_path)
    data_url = f"data:{mime};base64,{b64}"

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        "max_tokens": 2048,
    }

    resp = requests.post(
        f"{API_BASE}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=120,
    )

    if resp.status_code != 200:
        return {"error": f"API 返回 {resp.status_code}: {resp.text[:500]}"}

    data = resp.json()
    content = ""
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        pass

    usage = data.get("usage", {})
    return {
        "model": data.get("model", model),
        "content": content,
        "usage": usage,
    }


def main():
    if len(sys.argv) < 2:
        print("用法: python vision.py <图片路径> [提示词]", file=sys.stderr)
        print("", file=sys.stderr)
        print("环境变量:", file=sys.stderr)
        print("  SILICONFLOW_API_KEY — 硅基流动 API 密钥", file=sys.stderr)
        sys.exit(1)

    image_path = sys.argv[1]
    prompt = sys.argv[2] if len(sys.argv) > 2 else None

    result = call_vision_api(image_path, prompt)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
