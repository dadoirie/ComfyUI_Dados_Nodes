import atexit
import os
import signal
import subprocess
import time
import base64
import json
from io import BytesIO
import numpy as np
from PIL import Image
import torch
import requests
from comfy_api.latest import io
import nodes
import comfy.model_management

def _find_danyapi_pid():
    result = subprocess.run(
        ["pgrep", "-f", "python -m danyapi"],
        capture_output=True,
        text=True,
        check=False
    )
    if result.returncode == 0 and result.stdout.strip():
        pids = result.stdout.strip().split()
        if pids:
            return int(pids[0])
    return None

def _kill_danyapi_server():
    pid = _find_danyapi_pid()
    if pid is None:
        return
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(1)
        try:
            os.kill(pid, 0)
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
    except OSError:
        pass

atexit.register(_kill_danyapi_server)

def interrupt_processing(value=True):
    comfy.model_management.interrupt_current_processing(value)

class DN_DanyAPI(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="DN_DanyAPI",
            display_name="DanyAPI Chat (Vision)",
            category="Dado's Nodes/LLM",
            description="Chat via DanyAPI proxy with image support.",
            inputs=[
                io.String.Input(
                    "prompt",
                    multiline=True,
                    default="Describe this image.",
                    tooltip="Your text prompt."
                ),
                io.Image.Input(
                    "image",
                    optional=True,
                    tooltip="Optional image(s) to include. Multiple images are sent as separate image_url parts."
                ),
                io.String.Input(
                    "session_id",
                    default="",
                    tooltip="Optional: existing session_id to continue a multi‑turn chat."
                ),
                io.Combo.Input(
                    "model",
                    default="deepseek-v4-vision",
                    options=[
                        "deepseek-v4-flash",
                        "deepseek-v4-pro",
                        "deepseek-v4-vision",
                        "qwen3.8-max",
                        "qwen3.7-max",
                        "qwen3.7-plus",
                        "qwen3.6-plus",
                        "qwen3.5-plus"
                    ],
                    tooltip="Model name. DeepSeek models and various Qwen versions."
                ),
                io.Boolean.Input(
                    "thinking",
                    default=False,
                    tooltip="Enable reasoning/thinking."
                ),
                io.Boolean.Input(
                    "search",
                    default=False,
                    tooltip="Enable web search (DeepSeek flash only)."
                ),
                io.String.Input(
                    "api_base",
                    default="http://127.0.0.1:8000/v1",
                    tooltip="DanyAPI server URL."
                ),
            ],
            outputs=[
                io.String.Output(display_name="response"),
                io.String.Output(display_name="session_id"),
                io.String.Output(display_name="reasoning"),
            ]
        )

    @classmethod
    def execute(cls, prompt, image, session_id, model, thinking, search, api_base):
        if nodes.before_node_execution():
            interrupt_processing(True)
            raise RuntimeError("Execution interrupted by user")

        url = f"{api_base.rstrip('/')}/chat/completions"
        content = [{"type": "text", "text": prompt}]

        if image is not None:
            if isinstance(image, torch.Tensor):
                if image.dim() == 4:
                    images = [image[i] for i in range(image.shape[0])]
                else:
                    images = [image]
            elif isinstance(image, (list, tuple)):
                images = image
            else:
                images = [image]

            if len(images) > 1:
                print(f"⚠️ Multiple images ({len(images)}) detected. Sending all – DanyAPI may or may not support multiple images per request.")

            for img_tensor in images:
                if img_tensor.dim() == 4:
                    img_tensor = img_tensor[0]
                i = 255. * img_tensor.cpu().numpy()
                img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
                buffered = BytesIO()
                img.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{img_str}"}
                })

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "thinking": thinking,
            "search": search,
            "stream": True,   # Required for immediate cancellation
        }
        if session_id:
            payload["session_id"] = session_id

        headers = {"Content-Type": "application/json"}

        with requests.post(url, json=payload, headers=headers, stream=True, timeout=120) as resp:
            resp.raise_for_status()
            content_type = resp.headers.get('content-type', '')

            # Case 1: JSON response (non‑stream)
            if 'application/json' in content_type:
                data = resp.json()
                choice = data.get("choices", [{}])[0] if data.get("choices") else {}
                message = choice.get("message", {})
                content_text = message.get("content", "")
                reasoning = message.get("reasoning_content", "")
                new_session_id = data.get("session_id", session_id)
                return io.NodeOutput(content_text, new_session_id, reasoning)

            # Case 2: SSE stream
            full_content = ""
            full_reasoning = ""
            conversation_id = session_id
            buffer = ""

            for chunk in resp.iter_content(chunk_size=1024, decode_unicode=True):
                if nodes.before_node_execution():
                    resp.close()
                    interrupt_processing(True)
                    raise RuntimeError("Execution interrupted by user")

                if chunk:
                    buffer += chunk
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                continue
                            try:
                                data = json.loads(data_str)
                            except json.JSONDecodeError:
                                continue

                            if "session_id" in data:
                                conversation_id = data["session_id"]

                            choice = data.get("choices", [{}])[0] if data.get("choices") else {}
                            delta = choice.get("delta", {})
                            if "content" in delta:
                                full_content += delta["content"]
                            if "reasoning_content" in delta:
                                full_reasoning += delta["reasoning_content"]

            if nodes.before_node_execution():
                interrupt_processing(True)
                raise RuntimeError("Execution interrupted by user after stream")

            return io.NodeOutput(full_content, conversation_id, full_reasoning)
