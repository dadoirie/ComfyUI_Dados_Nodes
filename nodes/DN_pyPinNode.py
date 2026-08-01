import contextlib
import io as io_module
import json
import random
import hashlib
import os
import glob
import requests
import torch
import torch.nn.functional as F
from comfy_api.latest import io
from PIL import Image
import numpy as np

from py3pin.Pinterest import Pinterest
from .. import constants
from .utils.api_routes import register_operation_handler
from aiohttp import web

CACHE_DIR = os.path.join(constants.USER_DATA_DIR, "pypin_cache")

@contextlib.contextmanager
def suppress_specific_output():
    temp_stdout = io_module.StringIO()
    temp_stderr = io_module.StringIO()
    with contextlib.redirect_stdout(temp_stdout), contextlib.redirect_stderr(temp_stderr):
        yield
    output = temp_stdout.getvalue() + temp_stderr.getvalue()
    filtered_output = '\n'.join([line for line in output.split('\n')
                                 if not (line.startswith("No credentials stored [Errno 21] Is a directory:") and ".cred_root" in line)])
    print(filtered_output, end='')

def check_user_exists(username):
    cred_root = constants.BASE_DIR + "/.cred_root"
    with suppress_specific_output():
        pinterest = Pinterest(username=username, cred_root=cred_root)

    USER_RESOURCE = "https://www.pinterest.com/_ngjs/resource/UserResource/get/"
    options = {
        "isPrefetch": "false",
        "username": username,
        "field_set_key": "profile",
    }
    try:
        url = pinterest.req_builder.buildGet(url=USER_RESOURCE, options=options)
        pinterest.get(url=url)
        return True
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error occurred: {e}")
        if e.response.status_code == 404:
            print("User not found. Please check the username.")
            return False
        return False

def get_board_sections(pinterest, board_id, sections_map, max_images=100):
    sections = []
    section_batch = pinterest.get_board_sections(board_id=board_id)
    while section_batch:
        sections.extend(section_batch)
        section_batch = pinterest.get_board_sections(board_id=board_id)
    sections_data = {}
    for section in sections:
        section_id = section['id']
        title = section.get('title', '')
        processed_images = []
        
        print(f"Fetching pins for section: {title} (ID: {section_id})")
        pin_count = 0
        all_section_pins = []
        section_pins = pinterest.get_section_pins(section_id=section_id, page_size=50)
        while section_pins:
            print(f"Got {len(section_pins)} pins for section {title}")
            pin_count += len(section_pins)
            all_section_pins.extend(section_pins)
            for sec_pin in section_pins:
                if len(processed_images) >= max_images:
                    break
                if 'images' in sec_pin and 'orig' in sec_pin['images']:
                    orig_url = sec_pin['images']['orig']['url']
                    if orig_url.lower().endswith(('.png', '.jpg', '.jpeg')):
                        processed_images.append(orig_url)
            if len(processed_images) >= max_images:
                break
            section_pins = pinterest.get_section_pins(section_id=section_id, page_size=50)
        
        print(f"Section {title}: {pin_count} pins")
        display_name = f"{title} ({pin_count})" if title else f"Unnamed ({pin_count})"
        sections_map[title] = section_id
        sections_data[section_id] = {
            "section-id": section_id,
            "title": title,
            "images": processed_images,
            "display_name": display_name
        }
    return sections_data

def get_board_images_via_feed(pinterest, board_id, board_name, max_images):
    max_images = round(max_images)
    all_pins = []
    batch_count = 0
    print(f"Starting board_feed for board {board_name}, max images: {max_images}")
    while len(all_pins) < max_images:
        feed_batch = pinterest.board_feed(board_id=board_id)
        if not feed_batch:
            break
        batch_count += 1
        remaining = max_images - len(all_pins)
        pins_to_add = feed_batch[:remaining]
        all_pins.extend(pins_to_add)
        print(f"Batch {batch_count}: {len(feed_batch)} pins available, added {len(pins_to_add)}, total so far: {len(all_pins)}")
        if len(all_pins) >= max_images:
            break
    print(f"Finished board_feed for board {board_name}, total pins: {len(all_pins)}")
    all_images = []
    for pin in all_pins:
        if "images" in pin and "orig" in pin["images"]:
            image_url = pin["images"]["orig"]["url"]
            all_images.append(image_url)
    print(f"Extracted {len(all_images)} image URLs")
    return all_images

def get_board_map(username):
    cred_root = constants.BASE_DIR + "/.cred_root"
    with suppress_specific_output():
        pinterest = Pinterest(username=username, cred_root=cred_root)
    boards = pinterest.boards(username=username, page_size=1000)

    board_map = {}
    for board in boards:
        board_id = board['id']
        board_name = board['name']
        board_map[board_name] = board_id
    return board_map

def get_board_data(pinterest, board, max_images):
    board_id = board['id']
    board_name = board['name']
    print("get_board_data called with " + board_name + " & " + board_id)
    processed_images = get_board_images_via_feed(pinterest, board_id, board_name, max_images)

    sections = {}
    sections_map = {}
    if board.get('section_count', 0) > 0:
        sections = get_board_sections(pinterest, board_id, sections_map, max_images)

    all_section_images = set()
    for sec_data in sections.values():
        all_section_images.update(sec_data.get('images', []))
    processed_images = [img for img in processed_images if img not in all_section_images]

    board_data = {
        "board-id": board_id,
        "board-name": board_name,
        "display_name": f"{board_name} ({len(processed_images)})",
        "sections": sections,
        "sections_map": sections_map,
        "images": processed_images
    }
    return board_data


def load_image_from_url(url):
    response = requests.get(url, timeout=5)
    img = Image.open(io_module.BytesIO(response.content))
    img = img.convert('RGB')
    img_array = np.array(img)
    img_tensor = torch.from_numpy(img_array).float() / 255.0
    return img_tensor.unsqueeze(0)

def strip_images(data):
    if isinstance(data, dict):
        stripped = {}
        for k, v in data.items():
            if k != 'images':
                stripped[k] = strip_images(v)
        return stripped
    elif isinstance(data, list):
        return [strip_images(item) for item in data]
    else:
        return data

def get_cached_usernames():
    if not os.path.exists(CACHE_DIR):
        return ["none"]
    files = glob.glob(os.path.join(CACHE_DIR, "*_boards.json"))
    usernames = ["none"]
    for f in files:
        basename = os.path.basename(f)
        if basename.endswith("_boards.json"):
            username = basename[:-12]
            usernames.append(username)
    return usernames

def handle_username_data_fetch(username):
    if not check_user_exists(username):
        return {"error": "User not found"}

    board_map = get_board_map(username)
    return {"board_map": board_map}


class DN_pyPinNode(io.ComfyNode):
    instance_caches = {}
    current_username = None
    _instance_state = {}

    """ def _reset_pools(self):
        self.current_pools = {}
        self.used_pools = {}
        self.last_boards = {}
        self.last_sections = {} """

    @classmethod
    def _get_instance_state(cls, unique_id):
        if unique_id not in cls._instance_state:
            cls._instance_state[unique_id] = {
                'current_pools': {},
                'used_pools': {},
                'last_boards': {},
                'last_sections': {},
            }
        return cls._instance_state[unique_id]

    @classmethod
    def _reset_pools(cls, unique_id):
        state = cls._get_instance_state(unique_id)
        state['current_pools'] = {}
        state['used_pools'] = {}
        state['last_boards'] = {}
        state['last_sections'] = {}
    
    @classmethod
    def _get_all_images(cls, selected_board, section, boards):
        if selected_board == 'all':
            all_images = []
            for board_data in boards.values():
                all_images.extend(board_data.get('images', []))
                for sec_data in board_data.get('sections', {}).values():
                    all_images.extend(sec_data.get('images', []))
            return all_images
        
        board_data = next(
            (b for b in boards.values() if b.get('board-name') == selected_board),
            None
        )
        if not board_data:
            return []
        
        board_images = board_data.get('images', [])
        sections = board_data.get('sections', {})
        sections_map = board_data.get('sections_map', {})
        
        if section == 'included':
            all_images = board_images.copy()
            for sec_data in sections.values():
                all_images.extend(sec_data.get('images', []))
            return all_images
        
        if section == 'excluded':
            return board_images
        
        if section in sections_map:
            sec_id = sections_map[section]
            if sec_id in sections:
                return sections[sec_id].get('images', [])
        
        return []
    
    @classmethod
    def _select_chaotic_draw(cls, all_images, unique_id, board, section):
        if not all_images:
            return ''
        state = cls._get_instance_state(unique_id)
        state['last_boards'][unique_id] = board
        state['last_sections'][unique_id] = section
        return random.choice(all_images)
    
    # OLD _select_fixed logic (commented out for revert)
    # def _select_fixed(self, all_images, unique_id, board, section, last_image):
    #     last_board = self.last_boards.get(unique_id)
    #     last_section = self.last_sections.get(unique_id)
    #     changed = last_board != board or last_section != section
    #
    #     if changed or not last_image:
    #         if not all_images:
    #             return ''
    #         self.last_boards[unique_id] = board
    #         self.last_sections[unique_id] = section
    #         return random.choice(all_images)
    #     return last_image

    @classmethod
    def _select_fixed(cls, all_images, unique_id, board, section, last_image, image_output):
        if image_output == 'fixed' and last_image and last_image in all_images:
            state = cls._get_instance_state(unique_id)
            state['last_boards'][unique_id] = board
            state['last_sections'][unique_id] = section
            return last_image
        
        if not all_images:
            return ''
        
        selected = random.choice(all_images)
        state = cls._get_instance_state(unique_id)
        state['last_boards'][unique_id] = board
        state['last_sections'][unique_id] = section
        return selected
    
    @classmethod
    def _select_circular_shuffle(cls, all_images, unique_id, board, section):
        state = cls._get_instance_state(unique_id)
        last_board = state['last_boards'].get(unique_id)
        last_section = state['last_sections'].get(unique_id)
        changed = last_board != board or last_section != section

        if changed or unique_id not in state['current_pools']:
            state['last_boards'][unique_id] = board
            state['last_sections'][unique_id] = section
            state['current_pools'][unique_id] = random.sample(all_images, len(all_images)) if all_images else []
            state['used_pools'][unique_id] = []

        if unique_id not in state['current_pools'] or not state['current_pools'][unique_id]:
            return ''

        selected_image = random.choice(state['current_pools'][unique_id])
        state['current_pools'][unique_id].remove(selected_image)
        state['used_pools'][unique_id].append(selected_image)

        if not state['current_pools'][unique_id]:
            state['current_pools'][unique_id] = random.sample(state['used_pools'][unique_id], len(state['used_pools'][unique_id])) if state['used_pools'][unique_id] else []
            state['used_pools'][unique_id] = []

        return selected_image

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="DN_pyPinNode",
            display_name="Pinterest Image Node",
            category="Dado's Nodes",
            description="Fetch images from Pinterest boards and sections",
            inputs=[
                io.String.Input("node_configs", default="{}", multiline=False),
                io.String.Input("pinterest_data", default="{}", multiline=False),
                io.String.Input("username", default="", multiline=False)
            ],
            outputs=[
                io.Image.Output(display_name="image"),
                io.Custom("JSON").Output(display_name="configs"),
                io.Custom("JSON").Output(display_name="data")
            ],
            hidden=[
                io.Hidden.unique_id
            ],
            is_output_node=True
        )

    @classmethod
    def execute(cls, node_configs, pinterest_data, username):
        unique_id = cls.hidden.unique_id
        configs = json.loads(node_configs) if node_configs else {}
        data = {}
        api_requests = configs.get('api_requests', 'cached')
        state = cls._get_instance_state(unique_id)
        
        if api_requests == "live":
            data = cls.instance_caches.get(unique_id)
        elif api_requests == "cached":
            cache_path = os.path.join(CACHE_DIR, f"{username}_boards.json")
            with open(cache_path, 'r') as f:
                data = json.load(f)

        if configs.get('reset_pool'):
            cls._reset_pools(unique_id)
            configs['last_boards_hash'] = None
            configs['reset_pool'] = False

        image_output, board, section, last_image, resize_image = [
            configs.get(k) for k in ('image_output', 'board', 'section', 'last_image', 'resize_image')
        ]
        boards = data.get('boards')

        if board and section and unique_id not in state['last_boards']:
            state['last_boards'][unique_id] = board
            state['last_sections'][unique_id] = section

        boards_str = json.dumps(boards, sort_keys=True)
        current_hash = hashlib.md5(boards_str.encode()).hexdigest()
        if configs.get('last_boards_hash') != current_hash:
            cls._reset_pools(unique_id)
            configs['last_boards_hash'] = current_hash
            
            if board and section:
                state['last_boards'][unique_id] = board
                state['last_sections'][unique_id] = section

        all_images = cls._get_all_images(board, section, boards)
        
        mode_strategies = {
            'chaotic draw': lambda: cls._select_chaotic_draw(all_images, unique_id, board, section),
            'fixed': lambda: cls._select_fixed(all_images, unique_id, board, section, last_image, image_output),
            'circular shuffle': lambda: cls._select_circular_shuffle(all_images, unique_id, board, section)
        }
        
        selection_strategy = mode_strategies.get(image_output)
        selected_image = selection_strategy() if selection_strategy else ''

        configs['last_image'] = selected_image
        img_tensor = load_image_from_url(selected_image)

        if resize_image:
            resize_str = str(resize_image).strip()
            if resize_str.isdigit() and int(resize_str) > 0:
                target_longest = int(resize_str)
                _, h, w, _ = img_tensor.shape
                if h == w:
                    new_h = new_w = target_longest
                else:
                    longest = max(h, w)
                    scale = target_longest / longest
                    new_h = int(h * scale)
                    new_w = int(w * scale)
                img_tensor = F.interpolate(img_tensor.permute(0, 3, 1, 2), size=(new_h, new_w), mode='bilinear', align_corners=False).permute(0, 2, 3, 1)

        pretty_configs = json.dumps(configs, indent=2)
        pretty_data = json.dumps(data, indent=2)
        stripped_pretty_data = json.dumps(strip_images(data), indent=2)

        return io.NodeOutput(
            img_tensor, pretty_configs, pretty_data,
            ui={
                "node_configs": pretty_configs,
                "pinterest_data": stripped_pretty_data
            }
        )

    @classmethod
    def fingerprint_inputs(cls, **kwargs):
        return random.random()

@register_operation_handler
async def handle_username_changed(request):
    """Handle username change messages from frontend"""
    data = await request.json()

    operation = data.get('operation')
    if operation not in ['username_changed', 'board_selected', 'remove_boards_cache', 'switch_to_cached', 'get_cached_usernames', 'load_cached_data', 'get_pinterest_pins']:
        return None
        
    node_id = str(data.get('id', 'unknown'))

    if operation == 'username_changed':
        # node_id = str(data.get('id', ''))
        payload = data.get('payload', {})
        username = payload.get('username', '')
        max_images = round(payload.get('max_images'))
        result = handle_username_data_fetch(username)
        
        return web.json_response({"data": result})
    if operation == 'board_selected':
        node_id = str(data.get('id'))
        payload = data.get('payload', {})
        username = payload.get('username')
        board_name = payload.get('board_name')
        max_images = round(payload.get('max_images'))
        api_requests = payload.get('api_requests')
        if not check_user_exists(username):
            return web.json_response({"error": "User not found"}, status=400)
        cred_root = constants.BASE_DIR + "/.cred_root"
        with suppress_specific_output():
            pinterest = Pinterest(username=username, cred_root=cred_root)
        boards = pinterest.boards(username=username, page_size=1000)
        fresh_board_map = {board['name']: board['id'] for board in boards}
        os.makedirs(CACHE_DIR, exist_ok=True)
        cached_file = os.path.join(CACHE_DIR, f"{username}_boards.json")
        if not board_name or board_name == 'all':
            all_boards_data = {}
            for i, board in enumerate(boards):
                board_data = get_board_data(pinterest, board, max_images)
                all_boards_data[board['id']] = board_data
            print("All boards processed")
            if api_requests == "live":
                DN_pyPinNode.instance_caches[node_id] = {"boards": all_boards_data, "board_map": fresh_board_map}
            elif api_requests == "cached":
                cache_data = {
                    "boards": all_boards_data,
                    "board_map": fresh_board_map
                }
                
                with open(cached_file, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f)
                
            stripped_boards = strip_images(all_boards_data)
            cached_usernames = get_cached_usernames()
            if api_requests == "cached":
                if username not in cached_usernames:
                    cached_usernames.append(username)
            return web.json_response({"data": stripped_boards, "board_map": fresh_board_map, "cached_usernames": cached_usernames})
        else:
            board_id = fresh_board_map.get(board_name)
            if not board_id:
                return web.json_response({"error": "Board not found"}, status=400)
            board = next((b for b in boards if b['id'] == board_id), None)
            if not board:
                return web.json_response({"error": "Board not found"}, status=400)
            board_data = get_board_data(pinterest, board, max_images)
            if api_requests == "live":
                existing_data = DN_pyPinNode.instance_caches.get(node_id, {"boards": {}, "board_map": {}})
                existing_data["boards"][board_id] = board_data
                existing_data["board_map"] = fresh_board_map
                DN_pyPinNode.instance_caches[node_id] = existing_data
            elif api_requests == "cached":
                existing_data = {}
                if os.path.exists(cached_file):
                    with open(cached_file, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                else:
                    existing_data = {"boards": {}, "board_map": {}}
                existing_data["boards"][board_id] = board_data
                existing_data["board_map"] = fresh_board_map
                with open(cached_file, 'w', encoding='utf-8') as f:
                    json.dump(existing_data, f)
            stripped_boards = strip_images(existing_data["boards"])
            cached_usernames = get_cached_usernames()
            if api_requests == "cached":
                if username not in cached_usernames:
                    cached_usernames.append(username)
            
            return web.json_response({"data": stripped_boards, "board_map": fresh_board_map, "cached_usernames": cached_usernames})
    elif operation == 'remove_boards_cache':
        node_id = str(data.get('id'))
        DN_pyPinNode.instance_caches.pop(node_id, None)
        return web.json_response({"status": "ok"})
    elif operation == 'switch_to_cached':
        node_id = str(data.get('id'))
        payload = data.get('payload', {})
        username = payload.get('username')
        if node_id in DN_pyPinNode.instance_caches and username:
            os.makedirs(CACHE_DIR, exist_ok=True)
            cached_file = os.path.join(CACHE_DIR, f"{username}_boards.json")
            with open(cached_file, 'w', encoding='utf-8') as f:
                json.dump(DN_pyPinNode.instance_caches[node_id], f)
            del DN_pyPinNode.instance_caches[node_id]
        return web.json_response({"status": "ok", "cached_usernames": get_cached_usernames()})
    elif operation == 'get_cached_usernames':
        return web.json_response({"cached_usernames": get_cached_usernames()})
    elif operation == 'load_cached_data':
        payload = data.get('payload', {})
        username = payload.get('username')
        cache_path = os.path.join(CACHE_DIR, f"{username}_boards.json")
        if os.path.exists(cache_path):
            with open(cache_path, 'r') as f:
                data = json.load(f)
            boards = strip_images(data.get('boards', {}))
            board_map = data.get('board_map', {})
        else:
            boards = {}
            board_map = {}
        return web.json_response({"data": boards, "board_map": board_map, "cached_usernames": get_cached_usernames()})
    elif operation == 'get_pinterest_pins':
        node_id = str(data.get('id'))
        payload = data.get('payload', {})
        username = payload.get('username')
        board_name = payload.get('board_name')
        section = payload.get('section')
        api_requests = payload.get('api_requests')
        
        if not check_user_exists(username):
            return web.json_response({"error": "User not found"}, status=400)
        cred_root = constants.BASE_DIR + "/.cred_root"
        with suppress_specific_output():
            pinterest = Pinterest(username=username, cred_root=cred_root)
        boards = pinterest.boards(username=username, page_size=1000)
        
        fresh_board_map = {}
        for board in boards:
            board_name_key = board["name"]
            board_id = board["id"]
            fresh_board_map[board_name_key] = board_id
            
        if api_requests == "live":
            data = DN_pyPinNode.instance_caches.get(node_id, {"boards": {}, "board_map": {}})
        elif api_requests == "cached":
            cache_path = os.path.join(CACHE_DIR, f"{username}_boards.json")
            if os.path.exists(cache_path):
                with open(cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {"boards": {}, "board_map": {}}
        
        boards_data = data.get("boards", {})
        
        pin_urls = []
        if board_name == "all":
            for board in boards_data.values():
                pin_urls.extend(board.get("images", []))
                for sec_data in board.get("sections", {}).values():
                    pin_urls.extend(sec_data.get("images", []))
        else:
            board_id = fresh_board_map.get(board_name)
            
            if not board_id:
                return web.json_response({"error": "Board not found"}, status=400)
            
            board_data = boards_data.get(board_id)
            
            if not board_data:
                return web.json_response({"error": "Board data not found"}, status=400)
                
            if section == "included":
                pin_urls.extend(board_data.get("images", []))
                for sec_data in board_data.get("sections", {}).values():
                    pin_urls.extend(sec_data.get("images", []))
            elif section == "excluded":
                pin_urls.extend(board_data.get("images", []))
            else:
                sections_map = board_data.get("sections_map", {})
                
                if section in sections_map:
                    sec_id = sections_map[section]
                    if sec_id in board_data.get("sections", {}):
                        pin_urls.extend(board_data["sections"][sec_id].get("images", []))
        
        return web.json_response({"pin_urls": pin_urls})
    return web.json_response({"error": "Invalid operation"}, status=400)
