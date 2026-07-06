"""Image generation tool handler (FAZA 16).

Migrated from electron/main.cjs `generateImage()`. Uses OpenAIImageClient to
generate an image with gpt-image and returns it as an image artifact. When the
response includes base64 data, it is also saved to the data dir so the artifact
panel can reference a local file (same behavior as the legacy handler).

Risk: low (image generation, no confirmation required). Output is saved as an
artifact (per IMPLEMENTATION_PLAN FAZA 15 rule 4: "Image output se čuva kao
artifact").
"""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.services.openai_image_client import OpenAIImageClient


def make_handlers(client: OpenAIImageClient, images_dir: Path) -> dict[str, Any]:
    def image_generate(arguments: dict[str, Any]) -> dict[str, Any]:
        prompt = str(arguments.get("prompt") or "")
        if not prompt.strip():
            raise ValueError("image_generate requires a non-empty 'prompt' string argument.")
        size = str(arguments.get("size") or "1024x1024")

        result = client.generate(prompt=prompt, size=size)
        b64 = result.get("b64_json")
        url = result.get("url")

        if b64:
            images_dir.mkdir(parents=True, exist_ok=True)
            image_path = images_dir / f"ricky-image-{uuid4().hex[:12]}.png"
            image_path.write_bytes(base64.b64decode(b64))
            return {
                "path": str(image_path),
                "artifact": {
                    "title": "Generated Image",
                    "kind": "image",
                    "content": f"data:image/png;base64,{b64}",
                },
            }
        if url:
            return {
                "url": url,
                "artifact": {
                    "title": "Generated Image",
                    "kind": "image",
                    "content": url,
                },
            }
        # Should not happen — client raises AppError on empty response.
        raise RuntimeError("Image response did not include image data.")

    return {"image_generate": image_generate}
