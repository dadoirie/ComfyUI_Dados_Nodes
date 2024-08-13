import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Dirs:
    @property
    def BASE_DIR(self):
        return BASE_DIR

dirs = Dirs()

from .nodes.pinterest_image import *

NODE_CLASS_MAPPINGS = {
    "PinterestImageNode": PinterestImageNode
}
NODE_DISPLAY_NAME_MAPPINGS = {
  "PinterestImageNode": "Pinterest Image"
  }

WEB_DIRECTORY = "./web/js"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY", "dirs"]

