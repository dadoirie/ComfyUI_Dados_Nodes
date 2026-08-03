import os
import subprocess
import tempfile
import numpy as np
import torch
from PIL import Image
from comfy_api.latest import io


class DN_VideoLastFrame(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="DN_VideoLastFrame",
            display_name="Video Last Frame",
            category="Dado's Nodes/Video",
            description="Extract the last frame of an mp4 video as an image",
            inputs=[
                io.String.Input("mp4_path", force_input=True),
            ],
            outputs=[
                io.Image.Output(),
            ],
        )

    @classmethod
    def execute(cls, mp4_path):
        if not mp4_path or not os.path.isfile(mp4_path):
            raise ValueError(f"mp4_path does not exist: {mp4_path}")

        with tempfile.TemporaryDirectory() as tmp_dir:
            frame_path = os.path.join(tmp_dir, "last_frame.png")
            command = [
                "ffmpeg", "-y",
                "-sseof", "-3",
                "-i", mp4_path,
                "-update", "1",
                "-q:v", "2",
                frame_path,
            ]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8", check=False)
            if not os.path.isfile(frame_path):
                raise ValueError(f"Failed to extract last frame from {mp4_path}: {result.stderr}")

            img = Image.open(frame_path).convert("RGB")
            img_tensor = torch.from_numpy(np.array(img).astype(np.float32) / 255.0).unsqueeze(0)

        return io.NodeOutput(img_tensor)
