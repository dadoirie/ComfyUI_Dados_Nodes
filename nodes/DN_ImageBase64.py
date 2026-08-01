import base64
import torch
import numpy as np
from PIL import Image
from io import BytesIO
from comfy_api.latest import io

class DN_ImageToBase64Node(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="DN_ImageToBase64Node",
            display_name="Image to Base64",
            category="Dado's Nodes/Image",
            description="Converts an image tensor to a base64 string",
            inputs=[
                io.Image.Input("image")
            ],
            outputs=[
                io.String.Output(display_name="base64_string")
            ]
        )

    @classmethod
    def execute(cls, image):
        base64_strings = []
        for img_tensor in image:
            i = 255. * img_tensor.numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
            
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
            base64_strings.append(img_str)
        
        result = base64_strings[0] if len(base64_strings) == 1 else ",".join(base64_strings)
        return io.NodeOutput(result)

class DN_Base64ToImageNode(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="DN_Base64ToImageNode",
            display_name="Base64 to Image",
            category="Dado's Nodes/Image",
            description="Converts a base64 string to an image tensor",
            inputs=[
                io.String.Input("base64_string", force_input=True)
            ],
            outputs=[
                io.Image.Output(display_name="image")
            ]
        )

    @classmethod
    def execute(cls, base64_string):
        if base64_string is None:
            raise ValueError("Base64 string input cannot be None")
            
        if isinstance(base64_string, str):
            if base64_string.startswith('data:image'):
                base64_string = base64_string.split(',')[1]
            base64_strings = base64_string.split(',')
        else:
            base64_strings = [base64_string]
        
        images = []
        for b64_str in base64_strings:
            try:
                image_data = base64.b64decode(b64_str)
                img = Image.open(BytesIO(image_data)).convert("RGB")
                i = torch.from_numpy(np.array(img).astype(np.float32) / 255.0)[None,]
                images.append(i)
            except Exception as e:
                raise ValueError(f"Failed to decode or process base64 image: {str(e)}") from e
        
        if not images:
            raise ValueError("No valid images were processed from the base64 string(s)")
            
        return io.NodeOutput(torch.cat(images, dim=0))
