# flake8: noqa: E402
# pylint: disable=wrong-import-position
import os
import json
import folder_paths

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USER_DATA_DIR = os.path.join(folder_paths.get_user_directory(), "DadosNodes")
EXTENSION_NAME = os.path.basename(BASE_DIR)
MESSAGE_ROUTE = "/dadosNodes"

class Constants:
    @property
    def BASE_DIR(self):
        return BASE_DIR

    @property
    def USER_DATA_DIR(self):
        return USER_DATA_DIR

constants = Constants()

WEB_DIRECTORY = "./web/comfyui"
COMMON_DIRECTORY = "./web/common"

# Import the ComfyUI API
from comfy_api.latest import ComfyExtension, io
from .nodes.utils.api_routes import register_routes

from .nodes.DN_ReplicateBaseNode import DN_ReplicateNodeAlpha
from .nodes.DN_pyPinNode import DN_pyPinNode
from .nodes.DN_PreviewImage import DN_PreviewImage
from .nodes.DN_VideoLastFrame import DN_VideoLastFrame
from .nodes.DN_VideoMerge import DN_VideoMerge
from .nodes.DN_CSVMultiDropDownNode import DN_CSVMultiDropDownNode
from .nodes.DN_MemoryStorage import DN_MemoryStorage
from .nodes.DN_ImageBatcher import DN_ImageBatcher
from .nodes.DN_MultilineString import DN_MultilineString
from .nodes.DN_WildcardsProcessor import DN_WildcardsProcessor
from .nodes.DN_ImageBase64 import DN_ImageToBase64Node, DN_Base64ToImageNode
from .nodes.DN_PythonCode import DN_PythonCode
from .nodes.DN_DeepSeekChat import DN_DeepSeekChat
from .nodes.DN_DanyAPI import DN_DanyAPI

# Function to create a dynamic node class for a specific model
def create_replicate_node(model_identifier):
    """Create a dynamic node class for a specific Replicate model"""
    
    class_name = f"DN_Replicate_{model_identifier.replace('/', '_').replace('-', '_')}"
    
    # Create a new class that inherits from DN_ReplicateNodeAlpha
    dynamic_node_class = type(class_name, (DN_ReplicateNodeAlpha,), {
        '_replicate_model': model_identifier,
        '__module__': __name__,
    })
    
    return dynamic_node_class

model_types = ["Image", "Video"]
registered_nodes = [
        DN_pyPinNode,
        DN_PreviewImage,
        DN_VideoLastFrame,
        DN_VideoMerge,
        DN_MultilineString,
        DN_CSVMultiDropDownNode,
        DN_MemoryStorage,
        DN_ImageBatcher,
        DN_WildcardsProcessor,
        DN_PythonCode,
        DN_ImageToBase64Node,
        DN_Base64ToImageNode,
        DN_DeepSeekChat,
        DN_DanyAPI
    ]
registered_replicate_models = []



# Process each model type
for model_type in model_types:
    models_file = os.path.join(BASE_DIR, "configs", "replicate", model_type, "models.json")
    
    if os.path.exists(models_file):
        with open(models_file, 'r', encoding='utf-8') as f:
            models_config = json.load(f)
            
        # Create a node for each model in the config
        for model_key in models_config.keys():
            node_class = create_replicate_node(model_key)
            # Set the model_type in the class
            node_class.model_type = model_type
            globals()[node_class.__name__] = node_class
            registered_nodes.append(node_class)
            registered_replicate_models.append(model_key)
            
GREEN = '\033[32m'
RESET = '\033[0m'
indent = f"{' ' * 10}"
header = f"[{GREEN}Replicate models registered{RESET}]:"
body = f"\n{indent}".join(registered_replicate_models)
print(f"{header}\n{indent}{body}")

class DadosNodes(ComfyExtension):
    # must be declared as async
    async def get_node_list(self):
        return registered_nodes

# can be declared async or not, both will work
def comfy_entrypoint():
    return DadosNodes()

register_routes()


""" 
    #"inactivePinterestImageNode": "Pinterest Node (WIP - broken)",
    "DN_TextConcatenateNode": "Dynamic Text Concatenate",
    "DN_TextDropDownNode": "Text DropDown",
    "DN_WildcardPromptEditorNode": "Wildcard Prompt Editor (deprecation pending)",
    "DN_WildcardSelectorComposerV2": "Wildcard Selector/Composer",
    "DN_PromptSectionsExtractor": "Prompt Sections Extractor",
    "DN_SmolVLMNode": "SmolVLM Image Describer",
    # "PinterestNode": "Pinterest Node",
    "DN_JoyTaggerNode": "JoyTagger",
    "DN_PixAITaggerNode": "PixAI Tagger",
    "DN_TagOpsNode": "TagOps",
 """
