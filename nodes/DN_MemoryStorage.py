import os
import random
import json

from .utils.api_routes import register_operation_handler
from aiohttp import web
from .. import constants
from comfy_api.latest import io

CACHE_DIR = os.path.join(constants.USER_DATA_DIR, "memory_storage")
DN_STORAGE_DATA = {}

class DN_MemoryStorage(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="DN_MemoryStorage",
            display_name="Memory Storage",
            category="Dado's Nodes/Memory Storage",
            description="Store and retrieve values in memory",
            inputs=[
                io.String.Input("root_graph_id", default=""),
                io.Combo.Input("mode", default="get", options=["set", "get"]),
                io.Combo.Input("context", default="workflow", options=["workflow", "global"]),
                io.Boolean.Input("persistent", default=False),
                io.String.Input("key", default=""),
                io.String.Input("input", force_input=True, optional=True)
            ],
            outputs=[
                io.String.Output(display_name="output")
            ],
            hidden=[
                io.Hidden.unique_id
            ],
            is_output_node=True
        )

    @classmethod
    def execute(cls, root_graph_id, mode, context, key, persistent, input=None):
        if key == "":
            raise ValueError("Empty key")

        storage_key = root_graph_id if context == "workflow" else "global"

        value = None
        if mode == "set" and input is not None and input.strip() != "":
            if storage_key not in DN_STORAGE_DATA:
                DN_STORAGE_DATA[storage_key] = {}
            DN_STORAGE_DATA[storage_key][key] = input
            value = input
            
            if persistent:
                file_path = os.path.join(CACHE_DIR, f"{storage_key}.json")
                data = {}
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                data[key] = input
                os.makedirs(CACHE_DIR, exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f)
        
        if mode == "get":
            if storage_key not in DN_STORAGE_DATA:
                DN_STORAGE_DATA[storage_key] = {}
                
            if persistent:
                file_path = os.path.join(CACHE_DIR, f"{storage_key}.json")
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if key in data:
                            DN_STORAGE_DATA[storage_key][key] = data[key]
            
            if storage_key in DN_STORAGE_DATA and key in DN_STORAGE_DATA[storage_key]:
                value = DN_STORAGE_DATA[storage_key][key]
        
        return io.NodeOutput(value,)

    @classmethod
    def fingerprint_inputs(cls, **kwargs):
        return random.random()

@register_operation_handler
async def memory_storage_operations(request):
    data = await request.json()
    
    operation = data.get('operation')
    if operation not in ['dummy_op', 'delete_memory_storage']:
        return None
    
    payload = data.get('payload')
    
    if operation == 'dummy_op':
        rootGraphId = payload.get('rootGraphId')
        print(f"Received rootGraphId: {rootGraphId}")
        return web.json_response({"response": "got the dummy"})
    
    if operation == 'delete_memory_storage':
        rootGraphId = payload.get('rootGraphId')
        if rootGraphId in DN_STORAGE_DATA:
            del DN_STORAGE_DATA[rootGraphId]
            print(f"Deleted memory storage for rootGraphId: {rootGraphId}")
        
        file_path = os.path.join(CACHE_DIR, f"{rootGraphId}.json")
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Deleted memory storage file: {file_path}")
            
        return web.json_response({"status": "success"})
    
    return web.json_response({"error": "Invalid operation"}, status=400)
