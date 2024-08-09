import random
import torch
from py3pin.Pinterest import Pinterest
import numpy as np
from PIL import Image
import requests
from io import BytesIO

def pil2tensor(image):
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)

class PinterestImageNode:
    _board_names = ["all"]

    """ 
    ! currently inactive since having issues populating and instancing the board name input dropdown 
    """
    """ 
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "username": ("STRING", {"default": "", "multiline": False}),
                "board_name": (cls._board_names, {"default": "all"}),
                "update_board_names": ("BOOLEAN", {"default": False}),
                "pause_api_requests": ("BOOLEAN", {"default": False}),
            },
            "hidden": {"seed": "INT"},
        }
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "username": ("STRING", {"default": "", "multiline": False}),
                "board_name": ("STRING", {"default": "all", "multiline": False}),
                "update_board_names": ("BOOLEAN", {"default": False}),
                "pause_api_requests": ("BOOLEAN", {"default": False}),
            },
            "hidden": {"seed": "INT"},
        }

    RETURN_TYPES = ("IMAGE", "STRING")

    FUNCTION = "get_random_pinterest_image"
    CATEGORY = "pinterest"
    OUTPUT_NODE = True

    def onNodeCreated(self):
        self.username = ""
        self.board_name = "all"
        self._board_names = ["all"]
        self.update_board_names = False

    def get_random_pinterest_image(self, username, board_name, update_board_names, pause_api_requests):
        if not username:
            raise ValueError(f"No username provided")
        
        self.pinterest = Pinterest(username=username)

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

        if update_board_names and username:
            self._board_names = ["all"] + [board['name'] for board in boards]
        
        print(f"username: {username}")
        print(f"self._board_names: {self._board_names}")

        """ temporary fix for the board name dropdown"""
        board_names_string = "\n".join(self._board_names)

        if pins:
            random_pin = random.choice(pins)
            image_url = random_pin['images']['474x']['url']
            
            if image_url:
                response = requests.get(image_url)
                img = Image.open(BytesIO(response.content))
                img_tensor = pil2tensor(img)
                return (img_tensor, board_names_string)
            else:
                raise ValueError("No suitable image URL found in the pin data")
        else:
            raise ValueError(f"No pins found for the selected board(s) board_name: {board_name}")
    
    @classmethod
    def IS_CHANGED(cls, username, board_name, update_board_names, pause_api_requests, seed):
        if not pause_api_requests:
            return {"seed": random.randint(0, 2**2 - 1)}
        return False

""" 
! TODO

* - make the board name dropdown work
-- preferebly a button to update the board names

* - if having more then 1 node in the workflow they do behave blocking
-- meaning that each node will need to wait for the next node to finish before proving the image
--- and so on until the last node
---- annoying and hope 

* - pause the api requests is not working - try another approach
-- also needs thorough testing as it did work in another workflow
--- (which wasnt really a workflow and more like a test spitting out images)

* - github repo
"""