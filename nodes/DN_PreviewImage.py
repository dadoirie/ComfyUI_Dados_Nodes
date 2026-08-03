import os
import numpy as np
from PIL import Image
from comfy_api.latest import io
import folder_paths


class DN_PreviewImage(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="DN_PreviewImage",
            display_name="Preview Image (Dados Nodes)",
            category="Dado's Nodes/Image",
            description="Preview an image or an mp4 video path",
            inputs=[
                io.Image.Input("image", optional=True),
                io.String.Input("mp4_path", optional=True, force_input=True),
            ],
            outputs=[],
            is_output_node=True,
        )

    @classmethod
    def execute(cls, image=None, mp4_path=None):
        if image is None and mp4_path is None:
            return io.NodeOutput()

        if image is not None:
            output_dir = folder_paths.get_temp_directory()
            filename_prefix = "ComfyUI"
            full_output_folder, filename, counter, subfolder, filename_prefix = folder_paths.get_save_image_path(filename_prefix, output_dir)

            img_array = image.cpu().numpy()

            # Process first image in batch only
            batch_img = img_array[0]

            # Convert dtype if necessary
            if batch_img.dtype != np.uint8:
                batch_img = np.clip(255. * batch_img, 0, 255).astype(np.uint8)

            img = Image.fromarray(batch_img)

            file = f"{filename}_{counter:05}_.png"
            # Save image and return in ComfyUI's expected format
            file_path = os.path.join(full_output_folder, file)
            img.save(file_path)

            return io.NodeOutput(ui={
                "images": [{
                    "filename": file,
                    "subfolder": subfolder,
                    "type": "temp"
                }]
            })

        if mp4_path is not None and isinstance(mp4_path, str) and mp4_path.lower().endswith(".mp4"):
            # If it's an MP4 path, return it directly
            subfolder_path = os.path.dirname(mp4_path)
            comfyui_index = subfolder_path.find("ComfyUI/")
            after_comfyui = subfolder_path[comfyui_index + 8:]
            type_value = after_comfyui.split('/')[0]
            return io.NodeOutput(ui={
                "videos": [{
                    "filename": os.path.basename(mp4_path),
                    "subfolder": subfolder_path,
                    "type": type_value
                }]
            })

        return io.NodeOutput()
