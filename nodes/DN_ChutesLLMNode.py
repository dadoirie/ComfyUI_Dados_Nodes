import json
import requests
import base64
import io as io_module
from PIL import Image
import os
from .. import constants
from .utils.api_routes import register_operation_handler
from .utils.utils import get_setting
from aiohttp import web
from comfy_api.latest import io

_CHUTES_MODELS = [
    "moonshotai/Kimi-K2-Thinking",
    "MiniMaxAI/MiniMax-M2",
    "Qwen/Qwen2.5-VL-32B-Instruct",
    "Qwen/Qwen2.5-VL-72B-Instruct",
    "Qwen/Qwen3-VL-235B-A22B-Instruct",
    "Qwen/Qwen3-VL-235B-A22B-Thinking",
    "zai-org/GLM-4.5",
    "zai-org/GLM-4.6",
    "zai-org/GLM-4.6-turbo",
    "chutesai/Ling-1T-FP8",
    "meta-llama/Llama-3.3-70B-Instruct",
    "unsloth/gemma-3-4b-it",
    "unsloth/gemma-3-12b-it",
    "unsloth/gemma-3-27b-it",
    "unsloth/Mistral-Small-24B-Instruct-2501",
    "deepseek-ai/DeepSeek-V3-0324",
    "deepseek-ai/DeepSeek-R1",
    "NousResearch/DeepHermes-3-Llama-3-8B-Preview",
    "NousResearch/DeepHermes-3-Mistral-24B-Preview",
    "NousResearch/Hermes-4-14B",
    "NousResearch/Hermes-4-70B",
    "cognitivecomputations/Dolphin3.0-Mistral-24B"
]

_VISION_MODELS_CHUTES = [
    "Qwen/Qwen2.5-VL-32B-Instruct",
    "Qwen/Qwen2.5-VL-72B-Instruct",
    "Qwen/Qwen3-VL-235B-A22B-Instruct",
    "Qwen/Qwen3-VL-235B-A22B-Thinking"
]

LLM_PROMPTS_DIR = os.path.join(constants.USER_DATA_DIR, "chutes_llm_prompts")

def get_llm_prompts():
    """Get list of available prompt names"""
    if not os.path.exists(LLM_PROMPTS_DIR):
        return []
    return [f[:-5] for f in os.listdir(LLM_PROMPTS_DIR) if f.endswith('.json')]

def get_llm_prompt(prompt_name):
    """Get a specific prompt by name"""
    prompt_file = os.path.join(LLM_PROMPTS_DIR, f"{prompt_name}.json")
    if not os.path.exists(prompt_file):
        return None
    with open(prompt_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_llm_prompt(prompt_name, data):
    """Save a prompt to a file"""
    os.makedirs(LLM_PROMPTS_DIR, exist_ok=True)
    prompt_file = os.path.join(LLM_PROMPTS_DIR, f"{prompt_name}.json")
    with open(prompt_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def delete_llm_prompt(prompt_name):
    """Delete a prompt file"""
    prompt_file = os.path.join(LLM_PROMPTS_DIR, f"{prompt_name}.json")
    if os.path.exists(prompt_file):
        os.remove(prompt_file)

class DN_ChutesLLMNode(io.ComfyNode):
    CHUTES_MODELS = _CHUTES_MODELS
    VISION_MODELS = _VISION_MODELS_CHUTES

    MODEL_OPTIONS = [
        f"{model} (Vision)" if model in _VISION_MODELS_CHUTES else model
        for model in _CHUTES_MODELS
    ]

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="DN_ChutesLLMNode",
            display_name="Chutes LLM",
            category="Dado's Nodes",
            description="Generate text using Chutes AI models",
            inputs=[
                io.String.Input("system", default="", multiline=True, tooltip="Main prompt/instructions for the AI model."),
                io.String.Input("user", default="", multiline=True, tooltip="The user's message/query sent to the AI."),
                io.Combo.Input("model", default="zai-org/GLM-4.5", options=cls.MODEL_OPTIONS, tooltip="The AI model to use for text generation."),
                io.Float.Input("temperature", default=0.7, min=0.0, max=2.0, step=0.1, tooltip="Controls randomness in output. Lower values (0.0) make responses more deterministic, higher values (2.0) more creative and varied."),
                io.Int.Input("max_tokens", default=4056, min=1, max=20000, step=1, tooltip="Maximum number of tokens in the response. Lower values (1) limit response length, higher values (20000) allow longer responses."),
                io.Int.Input("seed", default=0, min=0, max=0xFFFFFFFFFFFFFFFF, step=1, tooltip="Random seed for reproducible outputs. Same seed generates identical responses."),
                io.Float.Input("top_p", default=1.0, min=0.0, max=1.0, step=0.01, tooltip="Nucleus sampling parameter. Lower values (0.0) make output more focused, higher values (1.0) more diverse."),
                io.Int.Input("top_k", default=-1, min=-1, max=1000, step=1, tooltip="Top-k sampling parameter. Number of top tokens to consider (-1 = no limit). Higher values make sampling more restrictive."),
                io.Image.Input("image", optional=True, tooltip="Optional image input for vision-capable models."),
                io.String.Input("text", force_input=True, optional=True, tooltip="Additional text input to append to the user message.")
            ],
            outputs=[
                io.String.Output(display_name="thinking"),
                io.String.Output(display_name="response"),
                io.Custom("JSON").Output(display_name="full_response")
            ]
        )

    @classmethod
    def _image_to_base64_data_url(cls, image_tensor):
        arr = (image_tensor.cpu().numpy() * 255).clip(0, 255).astype('uint8')

        pil_image = Image.fromarray(arr)

        buffer = io_module.BytesIO()
        pil_image.save(buffer, format="PNG")
        image_bytes = buffer.getvalue()

        base64_string = base64.b64encode(image_bytes).decode("utf-8")

        return f"data:image/png;base64,{base64_string}"

    @classmethod
    def execute(cls, system, user, model, image=None, text=None, temperature=0.7, max_tokens=4056, seed=0, top_p=1.0, top_k=-1):
        model = model.replace(" (Vision)", "")

        user_content = user
        if text:
            user_content += "\n\n" + text

        messages = [
            {"role": "system", "content": "[BASE]: " + system},
            {"role": "user", "content": "[USER]: " + user_content}
        ]

        if model in cls.VISION_MODELS and image is not None:
            content = [{"type": "text", "text": user_content}]
            for i in range(image.shape[0]):
                content.append({"type": "image_url", "image_url": {"url": cls._image_to_base64_data_url(image[i])}})
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": content}
            ]

        api_token = get_setting('dadosNodes.chutes_api_key')

        headers = {
            "Authorization": "Bearer " + api_token,
            "Content-Type": "application/json"
        }

        body = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "seed": seed,
            "top_p": top_p,
            "top_k": top_k
        }

        response = requests.post(
            "https://llm.chutes.ai/v1/chat/completions",
            headers=headers,
            json=body,
            timeout=3600
        )

        if response.status_code != 200:
            print(f"API request failed with status code {response.status_code}")
            print("Raw API error response content:")
            response_text = response.content.decode('utf-8')
            print(response_text)

            try:
                error_message = json.loads(
                    json.loads(response_text)['detail']
                    .replace("Invalid request: Invalid request: ", "", 1)
                )['detail']['message']
            except (json.JSONDecodeError, KeyError):
                outer_data = json.loads(response_text)
                error_message = outer_data['detail']
            
            print("Detailed API error message:")
            print(error_message)

            raise ValueError(f"API request failed with status code {response.status_code}. Details: {error_message}")

        complete_response = json.loads(response.content.decode('utf-8'))
        thinking = ""
        response = ""

        if complete_response.get("choices") and len(complete_response["choices"]) > 0:
            choice = complete_response["choices"][0]
            message = choice.get("message", {})
            thinking = (message.get("reasoning_content") or "").lstrip('\n')
            response = (message.get("content") or "").lstrip('\n')

            if not response and thinking:
                response = thinking
                thinking = ""

            if response and "<think>" in response and "</think>" in response:
                think_start_idx = response.find("<think>")
                think_end_idx = response.find("</think>")
                if think_start_idx < think_end_idx:
                    thinking = response[think_start_idx + 7:think_end_idx].lstrip('\n')
                    response = response[think_end_idx + 8:].lstrip('\n')
            elif response and "</think>" in response:
                think_end_idx = response.find("</think>")
                thinking = response[:think_end_idx].lstrip('\n')
                response = response[think_end_idx + 8:].lstrip('\n')

        return io.NodeOutput(thinking, response, complete_response)

@register_operation_handler
async def handle_llm_operations(request):
    data = await request.json()
    operation = data.get('operation')
    if operation not in ['get_all_llm_prompts', 'get_llm_prompt', 'store_llm_prompt', 'delete_llm_prompt']:
        return None

    if operation == 'get_all_llm_prompts':
        prompts = get_llm_prompts()
        return web.json_response({"prompts": prompts})

    if operation == 'store_llm_prompt':
        payload = data.get('payload', {})
        prompt_name = payload.get('prompt_name')
        if not prompt_name:
            return web.json_response({"status": "no_name"})

        save_llm_prompt(prompt_name, {
            "system": payload.get('system'),
            "user": payload.get('user'),
            "model": payload.get('model'),
            "temperature": payload.get('temperature'),
            "max_tokens": payload.get('max_tokens'),
            "seed": payload.get('seed'),
            "top_p": payload.get('top_p'),
            "top_k": payload.get('top_k')
        })
        return web.json_response({"status": "saved"})

    if operation == 'get_llm_prompt':
        payload = data.get('payload', {})
        prompt_name = payload.get('prompt_name')
        prompt_data = get_llm_prompt(prompt_name)
        if prompt_data:
            return web.json_response({"data": prompt_data})
        return web.json_response({"error": "Prompt not found"}, status=404)

    if operation == 'delete_llm_prompt':
        payload = data.get('payload', {})
        prompt_name = payload.get('prompt_name')
        delete_llm_prompt(prompt_name)
        return web.json_response({"prompts": get_llm_prompts()})

    return web.json_response({"error": "Invalid operation"}, status=400)
