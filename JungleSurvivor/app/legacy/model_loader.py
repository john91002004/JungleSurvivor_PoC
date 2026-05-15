"""
模型載入器 — 支援 Kaggle GPU 和本地 Ollama 兩種模式。

Kaggle 模式：使用 Transformers 載入 Gemma 4 E2B
本地模式：透過 Ollama API 呼叫（離線 Demo 用）
"""

import os
from typing import Optional
from PIL import Image

from config import MODEL_ID, MAX_NEW_TOKENS, DEFAULT_DTYPE


class GemmaModel:
    """Transformers 模式 — Kaggle 或有 GPU 的環境"""

    def __init__(self, model_id: str = MODEL_ID, device: str = "auto"):
        import torch
        from transformers import AutoProcessor, AutoModelForImageTextToText

        self.model_id = model_id
        self.processor = AutoProcessor.from_pretrained(model_id)

        device_map = device
        if device == "auto" and torch.cuda.device_count() > 1:
            device_map = {"": "cuda:0"}

        dtype = getattr(torch, DEFAULT_DTYPE, torch.bfloat16)
        self.model = AutoModelForImageTextToText.from_pretrained(
            model_id,
            torch_dtype=dtype,
            device_map=device_map,
        )
        self._device = self.model.device

    def generate(
        self,
        prompt: str,
        images: Optional[list[Image.Image]] = None,
        max_new_tokens: int = MAX_NEW_TOKENS,
    ) -> str:
        """
        執行多模態推理。

        Args:
            prompt: 文字 Prompt
            images: PIL Image 列表（可選）
            max_new_tokens: 最大生成 token 數

        Returns:
            模型的文字回覆
        """
        content = []

        if images:
            for img in images:
                content.append({"type": "image", "image": img})

        content.append({"type": "text", "text": prompt})

        messages = [{"role": "user", "content": content}]

        inputs = self.processor.apply_chat_template(
            messages,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
            add_generation_prompt=True,
        ).to(self._device)

        input_len = inputs["input_ids"].shape[-1]
        outputs = self.model.generate(**inputs, max_new_tokens=max_new_tokens)
        response = self.processor.decode(
            outputs[0][input_len:], skip_special_tokens=True
        )

        return response


class OllamaModel:
    """Ollama API 模式 — 本地離線 Demo"""

    def __init__(self, model_name: str = "gemma3:4b", base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url

    def generate(
        self,
        prompt: str,
        images: Optional[list[Image.Image]] = None,
        max_new_tokens: int = MAX_NEW_TOKENS,
    ) -> str:
        import requests
        import base64
        from io import BytesIO

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": max_new_tokens},
        }

        if images:
            encoded_images = []
            for img in images:
                buffer = BytesIO()
                img.save(buffer, format="JPEG")
                encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
                encoded_images.append(encoded)
            payload["images"] = encoded_images

        resp = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=300,
        )
        resp.raise_for_status()
        return resp.json().get("response", "")


def load_model(mode: str = "auto") -> GemmaModel | OllamaModel:
    """
    根據環境自動選擇模型載入方式。

    Args:
        mode: "kaggle" | "ollama" | "auto"
              auto 會偵測是否在 Kaggle 環境

    Returns:
        模型實例（GemmaModel 或 OllamaModel）
    """
    if mode == "ollama":
        return OllamaModel()

    if mode == "kaggle" or mode == "auto":
        try:
            import torch
            if torch.cuda.is_available():
                print(f"偵測到 GPU，使用 Transformers 載入 {MODEL_ID}...")
                return GemmaModel()
        except ImportError:
            pass

    if mode == "auto":
        print("未偵測到 GPU，嘗試使用 Ollama...")
        return OllamaModel()

    raise RuntimeError(f"無法載入模型，模式：{mode}")
