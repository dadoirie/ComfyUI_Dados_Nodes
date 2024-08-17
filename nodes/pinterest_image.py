import json
import random
import time
import contextlib
import io

from PIL import Image
import torch
import numpy as np
import requests
from aiohttp import web

from py3pin.Pinterest import Pinterest
from py3pin.RequestBuilder import RequestBuilder

# sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "comfy"))
from server import PromptServer  # type: ignore pylint: disable=import-error
import comfy.model_management  # type: ignore pylint: disable=import-error

from .. import constants

def interrupt_processing(value=True):
    comfy.model_management.interrupt_current_processing(value)

def pil2tensor(image):
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)

def get_data(data, *keys):
    return tuple(data.get(key) for key in keys)

@contextlib.contextmanager
def suppress_specific_output():
    temp_stdout = io.StringIO()
    with contextlib.redirect_stdout(temp_stdout):
        yield
    output = temp_stdout.getvalue()
    filtered_output = '\n'.join([line for line in output.split('\n')
                                 if not (line.startswith("No credentials stored [Errno 21] Is a directory:")
                                         and "/.cred_root" in line)])
    print(filtered_output, end='')

def check_user_exists(pinterest, username, unique_id):
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
            PromptServer.instance.send_sync('/dadoNodes/pinterestNode/' + str(unique_id), {
                "operation": "user_not_found",
                "message": "User not found. Please check the username."
            })
        return False

class PinterestImageNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "username": ("STRING", {"default": "", "multiline": False}),
                "image_output": (["fixed", "chaotic draw", "circular shuffle"], {"default": "chaotic draw"}),
                "api_requests": (["cached", "live"], {"default": "live"}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = ("IMAGE",)

    FUNCTION = "get_random_pinterest_image"
    CATEGORY = "pinterest"

    board_name = {}

    def __init__(self):
        self.pinterest = None
        self.last_image_url = {
            "img_tensor": None,
            "image_url": None,
            "metadata": None,
        }
        self.req_builder = RequestBuilder()

    @classmethod
    def update_board_name(cls, node_id, board_name):
        if node_id not in cls.board_name:
            cls.board_name[node_id] = {}
        cls.board_name[node_id]['board_name'] = board_name

    def get_random_pinterest_image(self, username, image_output, api_requests, unique_id):
        if not username:
            PromptServer.instance.send_sync('/dadoNodes/pinterestNode/' + str(unique_id), {
                "operation": "user_not_found",
                "message": "No username input provided."
            })
            # raise ValueError("No username input provided")
            interrupt_processing(True)
            return (None,)
        
        cred_root = constants.BASE_DIR + "/.cred_root"
        if self.pinterest is None:
            with suppress_specific_output():
                self.pinterest = Pinterest(username=username, cred_root=cred_root)

        if not check_user_exists(self.pinterest, username, unique_id):
            interrupt_processing(True)
            return (None,)

        if image_output == "fixed" and self.last_image_url["img_tensor"] is not None:
            PromptServer.instance.send_sync('/dadoNodes/pinterestNode/' + str(unique_id), {
                "operation": "result",
                "result": {
                    "board_name": PinterestImageNode.board_name[int(unique_id)],
                    "image_url": self.last_image_url["image_url"]}
            })
            return (self.last_image_url["img_tensor"],)

        if int(unique_id) not in PinterestImageNode.board_name or not PinterestImageNode.board_name[int(unique_id)]:
            print(f"requesting selected board name for {unique_id} node")
            PromptServer.instance.send_sync('/dadoNodes/pinterestNode/' + str(unique_id), {
                "operation": "get_selected_board",
                "node_id": unique_id
            })

            for _ in range(100):
                if int(unique_id) in PinterestImageNode.board_name:
                    break
                time.sleep(0.05)

            if int(unique_id) not in PinterestImageNode.board_name:
                raise ValueError("no board name found")

        board_name = PinterestImageNode.board_name[int(unique_id)]['board_name']

        print(f"Processing node with unique_id: {unique_id}")
        print("cred_root folder: ", cred_root)

        print(f"All board name: {PinterestImageNode.board_name}")

        print(f"Getting random Pinterest image from board '{board_name}' for user '{username}'")

        with suppress_specific_output():
            self.pinterest = Pinterest(username=username, cred_root=cred_root)

        pins = []
        boards = self.pinterest.boards(username=username)

        if board_name == "all":
            batch = self.pinterest.get_user_pins(username=username)
            while batch:
                pins.extend([pin for pin in batch if 'images' in pin and '474x' in pin['images']])
                batch = self.pinterest.get_user_pins(username=username)

        else:
            target_board = next(
                (board for board in boards if board['name'].lower() == board_name.lower()), None)
            if not target_board:
                raise ValueError(
                    f"Board '{board_name}' not found for user '{username}'")
            pins = [pin for pin in self.pinterest.board_feed(
                board_id=target_board['id']) if 'images' in pin and '474x' in pin['images']]

        if not pins:
            raise ValueError(
                f"No pins found for the selected board(s) board_name: {board_name}")

        while True:
            random_pin = random.choice(pins)
            if not random_pin.get('is_video', False):
                break
        image_url = random_pin['images']['474x']['url']

        """ # ! code for research purposes
        matching_pin = None
        for pin in pins:
            if pin is not None and isinstance(pin, dict):
                native_creator = pin.get('native_creator', {})
                if isinstance(native_creator, dict) and native_creator.get('type') != 'user':
                    matching_pin = pin
                    break

        if matching_pin:
            print(json.dumps(matching_pin, indent=2)) """

        if image_url:
            response = requests.get(image_url, timeout=30)
            img = Image.open(io.BytesIO(response.content))
            img_tensor = pil2tensor(img)

            # might be useful later
            metadata = json.dumps(random_pin, indent=2)
            # print(metadata)

            PromptServer.instance.send_sync('/dadoNodes/pinterestNode/' + str(unique_id), {
                "operation": "result",
                "result": {
                    "board_name": board_name,
                    "image_url": image_url}
            })
            self.last_image_url = {
                "img_tensor": img_tensor,
                "image_url": image_url,
                "metadata": metadata,
            }

            return (img_tensor,)

        raise ValueError("No suitable image URL found in the pin data")

    @classmethod
    def IS_CHANGED(cls):
        return random.randint(1, 1000000)

@PromptServer.instance.routes.post('/dadoNodes/pinterestNode/')
async def api_pinterest_router(request):
    data = await request.json()
    operation, username = get_data(data, 'op', 'username')

    if operation == 'get_pinterest_board_names':
        print(f"Getting Boards from Pinterest username: {username}")
        node_id = data.get('node_id')
        with suppress_specific_output():
            pinterest = Pinterest(username=username, cred_root=constants.BASE_DIR + "/.cred_root")
        if not check_user_exists(pinterest, username, node_id):
            interrupt_processing(True)
            return web.json_response({"error": "user not found"}, status=404)
        PromptServer.instance.send_sync('/dadoNodes/pinterestNode/' + str(node_id), {
            "operation": "user_found",
            "message": "user found",
        })
        boards = pinterest.boards(username=username)
        board_names = ["all"] + [board['name'] for board in boards]
        return web.json_response({"board_names": board_names})

    if operation == 'update_selected_board_name':
        board_name = data.get('board_name')
        node_id = data.get('node_id')
        print(f"Updating board for {username}: {board_name} (Node ID: {node_id})")
        PinterestImageNode.update_board_name(node_id, board_name)
        return web.json_response({"status": "success", "board_name": board_name})

    if operation == 'common_test':
        message = data.get('message')
        print(f"Received message: {message}")
        return web.json_response({"status": "success", "reply": "you got it"})

    return web.json_response({"error": "Unknown operation"}, status=400)
