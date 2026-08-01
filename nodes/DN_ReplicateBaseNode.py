import io as io_module
import time
import os
import json
from datetime import datetime
import urllib.request
from PIL import Image
from comfy_api.latest import io
import replicate
import torch
import numpy as np
import comfy.model_management
import folder_paths
import nodes
from .utils.utils import DN_ReplicateInputs
from .. import constants

import logging
httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.WARNING)

def tensor_to_bytes(tensor, mode):
    array = (tensor.cpu().numpy() * 255).astype(np.uint8)
    img = Image.fromarray(array, mode=mode)
    img_bytes = io_module.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes

def interrupt_processing(value=True):
    comfy.model_management.interrupt_current_processing(value)

class DN_ReplicateNodeAlpha(io.ComfyNode):
    _replicate_model = None
    _models_cache = _input_schema_cache = _output_schema_cache = _inputs_cache = model_type = None
    
    @classmethod
    def define_schema(cls) -> io.Schema:
        if cls._models_cache is None:
            file_path = os.path.join(
                constants.BASE_DIR, "configs", "replicate", cls.model_type, "models.json"
            )

            with open(file_path, encoding="utf-8") as f:
                cls._models_cache = json.load(f)

        if cls._replicate_model is None:
            raise ValueError("Subclass must set _replicate_model")
            
        if cls._input_schema_cache is None:
            schema_path = os.path.join(
                constants.BASE_DIR, "configs", "replicate", cls.model_type, "schemas", f"{cls._replicate_model.replace('/', '.')}.input.json"
            )

            with open(schema_path, encoding="utf-8") as f:
                cls._input_schema_cache = json.load(f)

        if cls._output_schema_cache is None:
            schema_path = os.path.join(
                constants.BASE_DIR, "configs", "replicate", cls.model_type, "schemas", f"{cls._replicate_model.replace('/', '.')}.output.json"
            )

            with open(schema_path, encoding="utf-8") as f:
                cls._output_schema_cache = json.load(f)

        if cls._inputs_cache is None:
            cls._inputs_cache = DN_ReplicateInputs.get_schema(cls._replicate_model, cls.model_type)
        return cls._inputs_cache
    
    @classmethod
    def execute(cls, **kwargs) -> io.NodeOutput:
        print("EXECUTING")
        print(f"{cls._replicate_model}:{cls._models_cache[cls._replicate_model]['version']}")
        input_data = {}
        for key, value in kwargs.items():
            if hasattr(value, 'shape'):
                if len(value.shape) == 4:
                    image_type = None
                    for prop_key, prop_value in cls._input_schema_cache["properties"].items():
                        if "image" in prop_key.lower() and "type" in prop_value:
                            image_type = prop_value["type"]
                            break
                            
                    if image_type == "array":
                        image_urls = []
                        for img_tensor in value:
                            img_bytes = tensor_to_bytes(img_tensor, 'RGB')
                            uploaded_file = replicate.files.create(file=img_bytes)
                            image_urls.append(uploaded_file.urls["get"])
                        input_data[key] = image_urls
                    elif image_type == "string":
                        img_bytes = tensor_to_bytes(value[0], 'RGB')
                        uploaded_file = replicate.files.create(file=img_bytes)
                        input_data[key] = uploaded_file.urls["get"]
                elif len(value.shape) == 3:  # Mask
                    value = value.squeeze(0)
                    mask_bytes = tensor_to_bytes(value, 'L')
                    uploaded_file = replicate.files.create(file=mask_bytes)
                    input_data[key] = uploaded_file.urls["get"]
            elif isinstance(value, (str, int, float, bool, type(None))):
                input_data[key] = value

        prediction = None
        model = replicate.models.get(cls._replicate_model)
        if cls._models_cache[cls._replicate_model]['version'] == "hidden":
            prediction = replicate.predictions.create(
                model=model,
                input=input_data
            )
        
        if cls._models_cache[cls._replicate_model]['version'] != "hidden":
            version = model.versions.get(cls._models_cache[cls._replicate_model]['version'])
            prediction = replicate.predictions.create(
                version=version,
                input=input_data
            )
        
        print(prediction)
        print(prediction.status)

        seen_logs = set()
        while prediction.status != 'succeeded':
            if prediction.status == 'failed':
                raise Exception(prediction.logs)
            if nodes.before_node_execution():
                prediction.cancel()
                prediction.reload()
                print(f"prediction status: {prediction.status}")
                time.sleep(0.25)
                interrupt_processing(True)
            prediction.reload()
            if prediction.logs:
                lines = prediction.logs.strip().split('\n')
                for line in lines:
                    if line and line not in seen_logs:
                        print(line)
                        seen_logs.add(line)
            time.sleep(0.25)
            
        output = prediction.output

        if not output:
            raise Exception("No output returned from Replicate API")
            
        if cls.model_type == "Image":
            image_tensors = []
            items = output if isinstance(output, list) else [output]
            
            for item in items:
                with urllib.request.urlopen(item) as response:
                    image_data = response.read()
                    img = Image.open(io_module.BytesIO(image_data))
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    img_array = np.array(img).astype(np.float32) / 255.0
                    img_array = np.expand_dims(img_array, 0)
                    image_tensor = torch.from_numpy(img_array)
                    image_tensors.append(image_tensor)
            
            if len(image_tensors) > 1:
                final_tensor = torch.cat(image_tensors, dim=0)
            else:
                final_tensor = image_tensors[0]
                
            return io.NodeOutput(final_tensor)
            
        if cls.model_type == "Video":
            temp_dir = folder_paths.get_temp_directory()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            video_filename = f"replicate_video_{timestamp}.mp4"
            video_path = os.path.join(temp_dir, video_filename)
            
            with urllib.request.urlopen(output) as response:
                with open(video_path, 'wb') as f:
                    f.write(response.read())
            
            return io.NodeOutput(video_path)
        
        raise NotImplementedError(f"Model type '{cls.model_type}' is not supported yet")