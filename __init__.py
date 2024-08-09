try:
  from .nodes.pinterest_image import *
except:
  print("Failed to load pinterest image node")

NODE_CLASS_MAPPINGS = {
    "PinterestImageNode": PinterestImageNode
}
