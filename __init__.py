from .nodes.pinterest_image import *

NODE_CLASS_MAPPINGS = {
    "PinterestImageNode": PinterestImageNode
}
NODE_DISPLAY_NAME_MAPPINGS = {
  "PinterestImageNode": "Pinterest Image"
  }

WEB_DIRECTORY = "./web/js"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]

