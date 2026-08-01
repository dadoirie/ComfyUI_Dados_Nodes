import os
from pathlib import Path
import json
import folder_paths
from ... import constants
from comfy_api.latest import io

class DN_Utils:
    """Utility class for common operations"""
    
    @staticmethod
    def load_json_file(filepath, file_description):
        """Load JSON file with consistent error handling"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"{file_description} file not found at: {filepath}")
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

class DN_ReplicateInputs:
    """Class for generating ComfyUI input definitions from Replicate model schemas"""
    
    @staticmethod
    def _create_schema(key, prop, schema_type):
        """Create input or output schema based on schema_type"""
        
        if schema_type == "input":
            prop_type = prop.get("type")
            config = {"method": None}

            if "description" in prop:
                config["tooltip"] = prop["description"]

            if "enum" in prop:
                config = {
                    "method": "Combo.Input",
                    "options": prop["enum"]
                }
            elif prop_type == "integer":
                config = {
                    "method": "Int.Input",
                    "min": prop.get("minimum"),
                    "max": prop.get("maximum"),
                    "step": 1,
                    "display_mode": io.NumberDisplay.number
                }
                if key == "seed":
                    config["max"] = 0xFFFFFFFFFFFFFFFF
            elif prop_type == "number":
                config = {
                    "method": "Float.Input",
                    "min": prop.get("minimum"),
                    "max": prop.get("maximum"),
                    "step": 0.1,
                    "display_mode": io.NumberDisplay.number
                }
            elif prop_type == "array":
                if "image" in key.lower():
                    config = {
                        "method": "Image.Input",
                        "optional": True
                    }
            elif prop_type == "string":
                config["method"] = "String.Input"
                if key in ("prompt", "negative_prompt", "loras", "lora_weights_transformer", "lora_weights_transformer_2") or key.startswith("adetailer") and key.endswith("prompt"):
                    config["multiline"] = True
                if prop.get("format") == "uri":
                    if "image" in key.lower():
                        config = {
                            "method": "Image.Input",
                            "optional": True
                        }
                    elif key == "mask":
                        config = {
                            "method": "Mask.Input",
                            "optional": True
                        }
            elif prop_type == "boolean":
                config["method"] = "Boolean.Input"
            
            default = prop.get("default")
            if default and default is not None:
                config["default"] = default

        elif schema_type == "output":
            prop_type = prop.get("type")
            config = {"method": None}
            
            if prop_type == "array" and prop.get("items").get("format") == "uri":
                if key == "Image":
                    config["method"] = "Image.Output"
            elif prop_type == "string" and prop.get("format") == "uri":
                if key == "Video":
                    config["method"] = "String.Output"
                if key == "Image":
                    config["method"] = "Image.Output"
        
        return config

    @staticmethod
    def _process_configs(configs):
        """Process a list of config dictionaries into their corresponding methods"""
        result = []
        for config in configs:
            method = getattr(io, config["method"].split(".")[0])
            method = getattr(method, config["method"].split(".")[1])
            
            args = config["args"]
            
            kwargs = {}
            for key, value in config.items():
                if key not in ["method", "args"]:
                    kwargs[key] = value
                    
            result.append(method(*args, **kwargs))
        return result

    @staticmethod
    def get_schema(model_key, model_type):
        """Generate ComfyUI input definitions from Replicate model schemas using Schema class"""
        
        models_config_path = os.path.join(constants.BASE_DIR, "configs", "replicate", model_type, "models.json")
        models_config = DN_Utils.load_json_file(models_config_path, "Models config")
        
        model_config = models_config.get(model_key)
        if not model_config:
            raise ValueError(f"Model '{model_key}' not found in models config")
            
        input_schema_path = os.path.join(constants.BASE_DIR, "configs", "replicate", model_type, "schemas", model_config.get("input_schema"))
        output_schema_path = os.path.join(constants.BASE_DIR, "configs", "replicate", model_type, "schemas", model_config.get("output_schema"))
        
        input_schema = DN_Utils.load_json_file(input_schema_path, "Input schema")
        output_schema = DN_Utils.load_json_file(output_schema_path, "Output schema")
        
        input_configs = []
        
        for key, prop in input_schema.get("properties").items():
            config = DN_ReplicateInputs._create_schema(key, prop, "input")
            config["args"] = [key]
                
            input_configs.append(config)
        
        output_configs = []
        config = DN_ReplicateInputs._create_schema(model_type, output_schema, "output")
        if config["method"]:
            config["args"] = ["output"]
            output_configs.append(config)
        
        return io.Schema(
            node_id=model_key,
            display_name=f"Replicate ({model_key})",
            category=f"Dado's Nodes/replicate/{model_type}",
            description=f"Replicate model: {model_key}",
            inputs=DN_ReplicateInputs._process_configs(input_configs),
            outputs=DN_ReplicateInputs._process_configs(output_configs)
        )

def get_chutes_inputs(model_key):
    """Generate ComfyUI input definitions from Chutes model schemas"""
    config_path = os.path.join(constants.BASE_DIR, "configs", "chutes", "image_gen", "models.json")

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Models config not found at: {config_path}")
    with open(config_path, 'r', encoding='utf-8') as f:
        models_config = json.load(f)

    models = models_config.get(model_key)
    if not models:
        raise ValueError(f"No models found for key: {model_key}")
    
    first_model = next(iter(models.values()))

    schema_path = os.path.join(constants.BASE_DIR, "configs", "chutes", "image_gen", "schemas", first_model["schema_file"])

    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"Schema file not found at: {schema_path}")
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_data = json.load(f)

    properties = schema_data["definitions"]["GenerationInput"]["properties"]

    preferred_order = {
        "prompt": "The text prompt describing what to generate",
        "negative_prompt": "Text describing what not to include in the output",
        "seed": "Random seed for reproducible results",
        "width": "Width of the output image in pixels",
        "height": "Height of the output image in pixels",
        "guidance_scale": "How strongly to follow the prompt",
        "true_cfg_scale": "How strongly to follow the prompt",
        "cfg": "How strongly to follow the prompt",
        "num_inference_steps": "Number of denoising steps"
    }

    input_defs = {}

    if len(models) > 1:
        input_defs["model"] = (list(models.keys()), {})

    for key in properties:
        if key not in preferred_order:
            raise ValueError(f"Unknown key '{key}' in schema")
    for key in preferred_order:
        if key in properties:
            input_defs[key] = _process_property(key, properties[key], preferred_order)

    if model_key in ["qwen"] and "true_cfg_scale" in input_defs:
        input_defs["guidance_scale"] = input_defs.pop("true_cfg_scale")

    result = {
        "input_defs": input_defs,
        "endpoint": first_model.get("endpoint")
    }
    return result

def _process_property(key, prop, preferred_order):
    """Convert schema property to ComfyUI input definition"""
    match key:
        case "prompt" | "negative_prompt":
            config = {
                "multiline": True,
                "tooltip": preferred_order[key]
            }
            return ("STRING", config)

        case "seed":
            integer_def = next(item for item in prop["anyOf"] if item["type"] == "integer")
            config = {
                "default": 0,
                "min": integer_def["minimum"],
                "max": integer_def["maximum"],
                "step": 1,
                "tooltip": preferred_order[key]
            }
            return ("INT", config)

        case "width" | "height":
            config = {
                "default": prop.get("default"),
                "min": prop.get("min", prop.get("minimum")),
                "max": prop.get("max", prop.get("maximum")),
                "step": 64,
                "tooltip": preferred_order[key]
            }
            return ("INT", config)

        case "num_inference_steps":
            config = {
                "default": prop.get("default"),
                "min": prop.get("min", prop.get("minimum")),
                "max": prop.get("max", prop.get("maximum")),
                "step": prop.get("step", 1),
                "tooltip": preferred_order[key]
            }
            return ("INT", config)

        case "guidance_scale" | "true_cfg_scale" | "cfg":
            config = {
                "default": prop.get("default"),
                "min": prop.get("min", prop.get("minimum")),
                "max": prop.get("max", prop.get("maximum")),
                "step": prop.get("step", 0.1),
                "tooltip": preferred_order[key]
            }
            return ("FLOAT", config)

def get_setting(setting_key):
    user_dir = folder_paths.get_user_directory()
    default_user = "default"  # TODO determine how to find the correct user - for now its 'default'
    settings_file = Path(user_dir) / default_user / "comfy.settings.json"
    if settings_file.exists():
        with open(settings_file, 'r', encoding='utf-8') as f:
            settings = json.load(f)
            return settings.get(setting_key)
    return None
        