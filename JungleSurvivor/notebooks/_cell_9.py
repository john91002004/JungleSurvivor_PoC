class GemmaModel:
    """Transformers 模式 — Kaggle 或有 GPU 的環境"""

    def __init__(self, model_id: str = MODEL_ID, device: str = "auto"):
        import torch
        from transformers import AutoProcessor, AutoModelForImageTextToText

        self.model_id = model_id
        self.processor = AutoProcessor.from_pretrained(model_id)

        dtype = getattr(torch, DEFAULT_DTYPE, torch.bfloat16)
        load_kwargs = {
            "device_map": "auto",
            "torch_dtype": dtype,
        }

        if USE_4BIT:
            from transformers import BitsAndBytesConfig
            load_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=dtype,
                bnb_4bit_quant_type="nf4",
            )

        self.model = AutoModelForImageTextToText.from_pretrained(
            model_id, **load_kwargs
        )
        self._device = next(self.model.parameters()).device

    @staticmethod
    def _resize_image(img: Image.Image, max_side: int = 512) -> Image.Image:
        w, h = img.size
        if max(w, h) <= max_side:
            return img
        ratio = max_side / max(w, h)
        new_size = (int(w * ratio), int(h * ratio))
        return img.resize(new_size, Image.LANCZOS)

    def generate(
        self,
        prompt: str,
        images: Optional[list[Image.Image]] = None,
        max_new_tokens: int = MAX_NEW_TOKENS,
    ) -> str:
        import torch
        import gc

        gc.collect()
        torch.cuda.empty_cache()

        content = []

        if images:
            for img in images:
                content.append({"type": "image", "image": self._resize_image(img)})

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

        with torch.inference_mode():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
            )

        response = self.processor.decode(
            outputs[0][input_len:], skip_special_tokens=True
        )

        del inputs, outputs
        gc.collect()
        torch.cuda.empty_cache()

        return response
