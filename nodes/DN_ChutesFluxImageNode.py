import io
import asyncio
import aiohttp
import torch
import numpy as np
from PIL import Image
import comfy.model_management
import nodes
from .utils.utils import get_chutes_inputs, get_setting

def interrupt_processing(value=True):
    comfy.model_management.interrupt_current_processing(value)

def check_interrupt(request_task):
    while not request_task.done():
        nodes.before_node_execution()

class APIExecutionHandle:
    def __init__(self, call_func, *args, **kwargs):
        self.call_func = call_func
        self.args = args
        self.kwargs = kwargs

    def execute(self):
        return self.call_func(*self.args, **self.kwargs)

class DN_ChutesFluxImageNode:
    _INPUTS = get_chutes_inputs("flux")
    _INPUT_DEFS = _INPUTS["input_defs"]
    _API_ENDPOINT = _INPUTS["endpoint"]
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": cls._INPUT_DEFS,
            "optional": {
                "parallel": ("BOOLEAN", {"default": False, "tooltip": "Enable parallel execution mode"}),
            }
        }

    RETURN_TYPES = ("IMAGE", "CHUTES_IMG_PARALLEL")
    RETURN_NAMES = ("image", "parallel")
    FUNCTION = "generate_image"
    CATEGORY = "Dado's Nodes/Chutes"

    def _process_seed(self, seed):
        """Convert 64-bit ComfyUI seeds to 32-bit for Chutes API"""
        if seed == 0:
            return None
        return seed & 0xFFFFFFFF

    async def _do_api_call(self, **kwargs):
        api_token = get_setting('dadosNodes.chutes_api_key')

        if not api_token:
            raise ValueError("Chutes API key needs to be set in the settings.")

        kwargs["seed"] = self._process_seed(kwargs.get("seed", 0))

        model = kwargs.get("model")
        num_inference_steps = kwargs["num_inference_steps"]
        num_inference_steps = num_inference_steps if model != "FLUX.1-dev" else min(num_inference_steps, 30)
        kwargs["num_inference_steps"] = num_inference_steps

        headers = {
            "Authorization": "Bearer " + api_token,
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            request_task = asyncio.create_task(session.post(self._API_ENDPOINT, headers=headers, json=kwargs))

            checker_task = asyncio.create_task(asyncio.to_thread(check_interrupt, request_task))
            done, pending = await asyncio.wait([request_task, checker_task], return_when=asyncio.FIRST_COMPLETED)

            if request_task in done:
                response = request_task.result()
                checker_task.cancel()

                if response.status != 200:
                    raise ValueError(f"API request failed with status code: {response.status}")

                image_bytes = await response.read()
                pil_image = Image.open(io.BytesIO(image_bytes))
                if pil_image.mode != "RGB":
                    pil_image = pil_image.convert("RGB")
                arr = np.array(pil_image).astype(np.float32) / 255.0
                tensor = torch.from_numpy(arr)
                return (tensor.unsqueeze(0),)
            
            checker_task.cancel()
            request_task.cancel()
            for task in pending:
                task.cancel()
            return None

    async def generate_image(self, **kwargs):
        parallel = kwargs.pop("parallel", False)
        if parallel:
            dummy = torch.zeros((1, 1, 1, 3), dtype=torch.float32)
            handle = APIExecutionHandle(self._do_api_call, **kwargs)
            return (dummy, handle)
        
        result = await self._do_api_call(**kwargs)
        if result is not None:
            return (result[0], None)
        
        interrupt_processing(True)
        return (None, None)

