import random
import torch
from py3pin.Pinterest import Pinterest
import numpy as np
from PIL import Image
import requests
from io import BytesIO

from server import PromptServer
from aiohttp import web
import json


def pil2tensor(image):
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)

class PinterestImageNode:
    def __init__(self):
        self.node_id = None
    
    node_board_names = {}

    @classmethod
    def update_board_name(cls, node_id, board_name):
        cls.node_board_names[node_id] = board_name

    @classmethod
    def get_board_name(cls, node_id):
        return cls.node_board_names.get(node_id, "all")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "username": ("STRING", {"default": "", "multiline": False}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            },
        }

    RETURN_TYPES = ("IMAGE",)

    FUNCTION = "get_random_pinterest_image"
    CATEGORY = "pinterest"

    def get_random_pinterest_image(self, username, seed):
        board_name = self.get_board_name(self.node_id)
        print(f"Getting random Pinterest image from board '{board_name}' for user '{username}' (Node ID: {self.node_id})")

        if not username:
            raise ValueError(f"No username provided")
        
        self.pinterest = Pinterest(username=username, cred_root='./cred_root')

        pins = []
        boards = self.pinterest.boards(username=username)
        if board_name == "all":
            for board in boards:
                pins.extend(self.pinterest.board_feed(board_id=board['id']))
        else:
            target_board = next((board for board in boards if board['name'].lower() == board_name.lower()), None)
            if not target_board:
                raise ValueError(f"Board '{board_name}' not found for user '{username}'")
            pins = self.pinterest.board_feed(board_id=target_board['id'])

        if not pins:
            raise ValueError(f"No pins found for the selected board(s) board_name: {board_name}")

        random_pin = random.choice(pins)
        image_url = random_pin['images']['474x']['url']
        
        if image_url:
            response = requests.get(image_url)
            img = Image.open(BytesIO(response.content))
            img_tensor = pil2tensor(img)
            return (img_tensor,)
        else:
            raise ValueError("No suitable image URL found in the pin data")


@PromptServer.instance.routes.post('/pinterestimageboard/get_board_names')
async def api_get_board_names(request):
    try:
        data = await request.json()
        username = data.get('username')
        print("Getting Boards from Pinterest username:", username)
        pinterestApi = Pinterest(username=username)
        boards = pinterestApi.boards(username=username)
        board_names = ["all"] + [board['name'] for board in boards]
        return web.json_response({"board_names": board_names})
    except Exception as e:
        print("Error parsing request body:", e)
        return web.json_response({"error": str(e)}, status=500)

@PromptServer.instance.routes.post('/pinterestimageboard/update_board')
async def api_update_board(request):
    try:
        data = await request.json()
        username = data.get('username')
        board_name = data.get('board_name')
        node_id = data.get('node_id')
        print(f"Updating board for {username}: {board_name} (Node ID: {node_id})")
        PinterestImageNode.update_board_name(node_id, board_name)
        print(f"Check update board for {username}: {board_name} (Node ID: {node_id}) > node_board_names[{node_id}]: {PinterestImageNode.node_board_names[node_id]}")
        return web.json_response({"status": "success", "board_name": board_name})
    except Exception as e:
        print("Error in update_board route:", e)
        return web.json_response({"error": str(e)}, status=500)

""" 
! TODO

* - targeting a specific board not working
-- issue is that FUNCTION and RETURN_TYPES need to be in the python file as it currently stands
-- if finding a way making these work in the javascript file would basically resolve this issue
-- javascript file needs the image either way in order to display the image in the node UI

"""