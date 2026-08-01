import torch
from PIL import Image
from pathlib import Path
from huggingface_hub import snapshot_download
from torchvision import transforms
import timm
import json
import folder_paths
from .. import constants

BASE_DIR = constants.BASE_DIR

MODEL_DIR = Path(BASE_DIR) / "models" / "pixaitagger"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

class TaggingHead(torch.nn.Module):
    def __init__(self, input_dim, num_classes):
        super().__init__()
        self.input_dim = input_dim
        self.num_classes = num_classes
        self.head = torch.nn.Sequential(torch.nn.Linear(input_dim, num_classes))

    def forward(self, x):
        logits = self.head(x)
        probs = torch.nn.functional.sigmoid(logits)
        return probs

def get_encoder():
    base_model_repo = "hf_hub:SmilingWolf/wd-eva02-large-tagger-v3"
    encoder = timm.create_model(base_model_repo, pretrained=False)
    encoder.reset_classifier(0)
    return encoder

def get_decoder():
    decoder = TaggingHead(1024, 13461)
    return decoder

def get_model():
    encoder = get_encoder()
    decoder = get_decoder()
    model = torch.nn.Sequential(encoder, decoder)
    return model

def download_pixaitagger():
    model_file = MODEL_DIR
    if model_file.exists():
        return str(MODEL_DIR)

    user_dir = folder_paths.get_user_directory()
    default_user = "default"  # TODO determine how to find the correct user - for now its 'default'
    settings_file = Path(user_dir) / default_user / "comfy.settings.json"

    hf_token = None
    if settings_file.exists():
        with open(settings_file, 'r', encoding='utf-8') as f:
            settings = json.load(f)
            hf_token = settings.get('dadosNodes.hf_token')

    if not hf_token:
        raise ValueError("Hugging Face access token needs to be set in the settings for PixAI Tagger.")
    
    path = snapshot_download(
        "pixai-labs/pixai-tagger-v0.9",
        local_dir=MODEL_DIR,
        token=hf_token,
        force_download=False,
        local_files_only=False,
        local_dir_use_symlinks="auto"
    )
    return path

def pure_pil_alpha_to_color_v2(
    image: Image.Image, color: tuple[int, int, int] = (255, 255, 255)
) -> Image.Image:
    image.load()
    background = Image.new("RGB", image.size, color)
    background.paste(image, mask=image.split()[3])
    return background


def pil_to_rgb(image: Image.Image) -> Image.Image:
    if image.mode == "RGBA":
        image = pure_pil_alpha_to_color_v2(image)
    elif image.mode == "P":
        image = pure_pil_alpha_to_color_v2(image.convert("RGBA"))
    else:
        image = image.convert("RGB")
    return image

class DN_PixAITaggerNode:
    _shared_model = None

    @classmethod
    def _get_shared_model(cls, model_path, target_device):
        if cls._shared_model is None or (cls._shared_model is not None and next(cls._shared_model.parameters()).device != target_device):
            if cls._shared_model is not None:
                print(f"Unloading PixAI Tagger model from {next(cls._shared_model.parameters()).device}...")
                cls._shared_model.cpu()
                del cls._shared_model
                torch.cuda.empty_cache()
                cls._shared_model = None
            
            print(f"Loading PixAI Tagger model to {target_device}...")
            cls._shared_model = get_model()
            states_dict = torch.load(Path(model_path) / "model_v0.9.pth", map_location=target_device, weights_only=True)
            cls._shared_model.load_state_dict(states_dict)
            cls._shared_model.to(target_device)
            cls._shared_model.eval()
            print(f"PixAI Tagger model loaded successfully on {target_device}")
        return cls._shared_model

    def __init__(self):
        self.model = None
        self.tag_map = None
        self.index_to_tag_map = None
        self.character_ip_mapping = None
        self.gen_tag_count = 0
        self.character_tag_count = 0
        self.current_device = None  # Track the currently loaded device
        self.transform = transforms.Compose(
            [
                transforms.Resize((448, 448)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]),
            ]
        )
        self.tags_to_exclude = {"web_address", "patreon_username", "gumroad_username", "artist_name"}
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "threshold_general": ("FLOAT", {
                    "default": 0.30,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.01,
                    "tooltip": "Minimum confidence score for general tags to be included. Higher scores may result in fewer tags."
                }),
                "threshold_character": ("FLOAT", {
                    "default": 0.85,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.01,
                    "tooltip": "Minimum confidence score for character tags to be included. Higher scores may result in fewer tags."
                }),
                "tags_count": ("INT", {
                    "default": 128,
                    "min": 1,
                    "max": 1000,
                    "step": 1,
                    "tooltip": "Maximum number of tags. Higher thresholds may result in fewer tags than this value."
                }),
                "exclude_tags": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "tooltip": "Exclude tags from the final generated tags. Tags with spaces or underscores will be treated as the same for matching.\nExample:'exlusion_one,exclusion two'"
                }),
                "underscore_separated": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "Use underscores instead of spaces between words in tags."
                }),
                "single_char_ip": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "If true, only use the top 1 character tag and its associated IP tags."
                }),
                "use_cpu": ("BOOLEAN", {"default": False, "tooltip": "If true, unload the model from GPU and use CPU instead."}),
                "keep_loaded": ("BOOLEAN", {"default": False, "tooltip": "If false, unload the model from memory after use."}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("tags",)
    FUNCTION = "generate_tags"
    CATEGORY = "Dado's Nodes/VLM Nodes"

    def _exclude_tags(self, exclude_tags):
        exclude_list = set()
        if exclude_tags.strip():
            for item in exclude_tags.split(','):
                cleaned = item.strip()
                if cleaned:
                    cleaned = cleaned.replace(' ', '_')
                    exclude_list.add(cleaned)
        return exclude_list

    def _remove_underscore(self, tag_name, underscore_separated):
        if not underscore_separated:
            tag_name = tag_name.replace("_", " ")
        return tag_name

    def _process_indices_for_tags(self, indices, probs, target_list):
        for i in indices:
            idx = i.item()
            tag_name = self.index_to_tag_map[idx]
            if tag_name not in self.tags_to_exclude:
                target_list.append((tag_name, probs[idx].item()))

    def generate_tags(self, image, threshold_general, threshold_character, tags_count, exclude_tags, underscore_separated, single_char_ip, use_cpu, keep_loaded):
        model_path = download_pixaitagger()
        
        target_device = "cpu" if use_cpu else ("cuda" if torch.cuda.is_available() else "cpu")

        if self.model is None or self.tag_map is None or self.character_ip_mapping is None or self.current_device != target_device:
            self.model = DN_PixAITaggerNode._get_shared_model(model_path, target_device)
            self.current_device = target_device
            
            tags_file = Path(model_path) / 'tags_v0.9_13k.json'
            mapping_file = Path(model_path) / 'char_ip_map.json'

            with open(tags_file, 'r') as f:
                tag_info = json.load(f)
                self.tag_map = tag_info["tag_map"]
                self.gen_tag_count = tag_info["tag_split"]["gen_tag_count"]
                self.character_tag_count = tag_info["tag_split"]["character_tag_count"]
                self.index_to_tag_map = {v: k for k, v in self.tag_map.items()}

            with open(mapping_file, 'r') as f:
                self.character_ip_mapping = json.load(f)
        
        pil_image = Image.fromarray((image[0].cpu().numpy() * 255).astype('uint8'))
        
        pil_image = pil_to_rgb(pil_image)
        image_tensor = self.transform(pil_image).unsqueeze(0).to(target_device)
        
        with torch.no_grad():
            with torch.amp.autocast_mode.autocast(target_device, enabled=True):
                probs = self.model.forward(image_tensor)[0]
            general_mask = probs[: self.gen_tag_count] > threshold_general
            character_mask = probs[self.gen_tag_count:] > threshold_character

            general_indices = general_mask.nonzero(as_tuple=True)[0]
            character_indices = (
                character_mask.nonzero(as_tuple=True)[0] + self.gen_tag_count
            )

            cur_gen_tags = []
            cur_char_tags = []
            
            self._process_indices_for_tags(general_indices, probs, cur_gen_tags)
            self._process_indices_for_tags(character_indices, probs, cur_char_tags)

            if single_char_ip:
                cur_char_tags.sort(key=lambda x: x[1], reverse=True)
                cur_char_tags = cur_char_tags[:1]

            cur_gen_tags.sort(key=lambda x: x[1], reverse=True)
            exclude_list = self._exclude_tags(exclude_tags)
            filtered_gen_tags = [tag for tag in cur_gen_tags if tag[0] not in exclude_list]
            final_gen_tags = filtered_gen_tags[:tags_count]
            
            processed_char_tags = []
            ip_tags_with_scores_map = {}

            for tag_name, score in cur_char_tags:
                current_char_tag_to_add = tag_name

                if tag_name in self.character_ip_mapping:
                    if "_(" in tag_name and tag_name.endswith(")"):
                        current_char_tag_to_add = tag_name.split("_(")[0]
                    
                    for ip_tag_name in self.character_ip_mapping[tag_name]:
                        ip_tags_with_scores_map[ip_tag_name] = max(ip_tags_with_scores_map.get(ip_tag_name, 0), score)
                
                processed_char_tags.append((current_char_tag_to_add, score))

            ip_tags_with_scores = sorted([(tag, score) for tag, score in ip_tags_with_scores_map.items()], key=lambda x: x[1], reverse=True)

            for i, (tag, score) in enumerate(ip_tags_with_scores):
                if "_(" in tag and tag.endswith(")"):
                    processed_tag = tag.split("_(")[0]
                    ip_tags_with_scores[i] = (processed_tag, score)

            char_and_ip_tags = processed_char_tags + ip_tags_with_scores
            char_and_ip_tags.sort(key=lambda x: x[1], reverse=True)

            for tag_list in [final_gen_tags, char_and_ip_tags]:
                tag_list[:] = [(tag.replace(':', ''), score) for tag, score in tag_list]

            unified_tags_data = char_and_ip_tags + final_gen_tags

            all_tags_str_list = []

            for tag_name, score in unified_tags_data:
                all_tags_str_list.append(self._remove_underscore(tag_name, underscore_separated))
            
            result_unified_tags = ', '.join(all_tags_str_list)

            # DEBUG: log scores for verification
            print("DEBUG: Tag scores:")
            for tag, score in unified_tags_data:
                print(f"  {tag}: {score}")

            result = (result_unified_tags,)

            if not keep_loaded:
                print(f"Unloading PixAI Tagger model from {self.current_device} after use.")
                if self.model is not None:
                    self.model.cpu()
                    del self.model
                    self.model = None
                self.tag_map = None
                self.index_to_tag_map = None
                self.character_ip_mapping = None
                self.current_device = None
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            
            return result
