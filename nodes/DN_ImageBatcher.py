import torch
from comfy_api.latest import io

class DN_ImageBatcher(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="DN_ImageBatcher",
            display_name="Image Batcher",
            category="Dado's Nodes/Image",
            description="Batch multiple images together",
            inputs=[
                io.Image.Input("image"),
                io.Image.Input("image_2"),
                io.Image.Input("image_3", optional=True),
            ],
            outputs=[
                io.Image.Output()
            ]
        )

    @classmethod
    def execute(cls, image, image_2, image_3=None):
        images = [img for img in [image, image_2, image_3] if img is not None]

        dims = [(img.shape[1], img.shape[2]) for img in images]
        max_dims = (max(h for h, w in dims), max(w for h, w in dims))

        if all(h == max_dims[0] and w == max_dims[1] for h, w in dims):
            return io.NodeOutput(torch.cat(images, dim=0))

        padded_images = []
        for img in images:
            h, w = img.shape[1], img.shape[2]
            if h == max_dims[0] and w == max_dims[1]:
                padded_images.append(img)
            else:
                padded = torch.zeros((img.shape[0], max_dims[0], max_dims[1], img.shape[3]), dtype=img.dtype, device=img.device)
                h_offset = (max_dims[0] - h) // 2
                w_offset = (max_dims[1] - w) // 2
                padded[:, h_offset:h_offset+h, w_offset:w_offset+w, :] = img
                padded_images.append(padded)

        return io.NodeOutput(torch.cat(padded_images, dim=0))