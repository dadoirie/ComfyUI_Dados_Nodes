import json
import os
import random

from .. import constants
from comfy_api.latest import io


class DN_MemoryStorage(io.ComfyNode):
    @staticmethod
    def _store_file() -> str:
        store_dir = os.path.join(constants.USER_DATA_DIR, "memory_storage")
        return os.path.join(store_dir, "store.json")

    @classmethod
    def _read_store(cls) -> dict:
        file_path = cls._store_file()
        if not os.path.exists(file_path):
            return {}
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}

    @classmethod
    def _write_store(cls, data: dict) -> None:
        file_path = cls._store_file()
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        tmp_path = file_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, file_path)

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="DN_MemoryStorage",
            display_name="Memory Storage",
            category="Dado's Nodes/Memory Storage",
            description="Store and retrieve a text value by key.",
            inputs=[
                io.Combo.Input("mode", default="get", options=["set", "get"]),
                io.String.Input("key", default=""),
                io.String.Input("input", force_input=True, optional=True),
            ],
            outputs=[
                io.String.Output(display_name="output"),
            ],
            is_output_node=True,
        )

    @classmethod
    def execute(cls, mode, key, input=None):
        key = (key or "").strip()
        if not key:
            raise ValueError("key must not be empty")

        if mode == "set":
            has_value = input is not None and input.strip() != ""
            if has_value:
                data = cls._read_store()
                data[key] = input
                cls._write_store(data)
                return io.NodeOutput(input)
            data = cls._read_store()
            if key not in data:
                raise ValueError(f"no value stored for key '{key}'")
            return io.NodeOutput(data[key])

        data = cls._read_store()
        if key not in data:
            raise ValueError(f"no value stored for key '{key}'")
        return io.NodeOutput(data[key])

    @classmethod
    def fingerprint_inputs(cls, **kwargs):
        return random.random()