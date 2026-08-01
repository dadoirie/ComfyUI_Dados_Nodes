"""
@title: CSV Multi DropDown
@author: Dado
@description: A node that accepts CSV input and outputs multiple dropdown selections
"""

from typing import Dict, ClassVar, List
import json
import random
import time
from aiohttp import web
from .utils.api_routes import register_operation_handler
from comfy_api.latest import io

class DN_CSVMultiDropDownNode(io.ComfyNode):
    """
    Node that outputs selections from multiple CSV-based dropdowns.
    """
    selections: ClassVar[Dict[str, Dict[str, str]]] = {}
    entries_map: ClassVar[Dict[str, Dict[str, List[str]]]] = {}
    DEFAULT_SELECTION = "empty"

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="DN_CSVMultiDropDownNode",
            display_name="CSV Multi DropDown",
            category="Dado's Nodes/Text & Prompt",
            description="A node that accepts CSV input and outputs multiple dropdown selections",
            inputs=[
                io.String.Input("csv_text", multiline=True, tooltip='Each line defines a dropdown. First item is the ID, rest are options.\nUse "random" to select a random option.\ncolor,"green,blue,yellow" & color,green,blue,yellow (both formats supported)'),
                io.Boolean.Input("remove_duplicates", default=False, tooltip="Remove duplicate entries in dropdowns")
            ],
            outputs=[
                io.String.Output(display_name="combined_selections")
            ] + [
                io.String.Output(display_name=str(i)) for i in range(1, 31)
            ],
            hidden=[
                io.Hidden.unique_id
            ]
        )

    @classmethod
    def execute(cls, csv_text, remove_duplicates):
        unique_id = cls.hidden.unique_id
        node_id = str(unique_id)
        selections_for_node = cls.selections.get(node_id, {})
        result_entries = []

        dropdown_order = []
        if csv_text:
            rows = csv_text.split('\n')
            for row in rows:
                row = row.strip()
                if not row:
                    continue
                parts = row.split(',')
                if len(parts) >= 2:
                    dropdown_id = parts[0].strip().strip('"')
                    dropdown_order.append(dropdown_id)

        for dropdown_id in dropdown_order:
            selection = selections_for_node.get(dropdown_id, cls.DEFAULT_SELECTION)
            if selection == "random":
                entries = cls.entries_map.get(node_id, {}).get(dropdown_id, [])
                selection = random.choice(entries) if entries else cls.DEFAULT_SELECTION
            result_entries.append(selection)

        combined = ", ".join(result_entries) if result_entries else cls.DEFAULT_SELECTION
        
        individual_outputs = []
        for i in range(30):
            if i < len(result_entries):
                individual_outputs.append(result_entries[i])
            else:
                individual_outputs.append("")
        
        return io.NodeOutput(combined, *individual_outputs)

    @classmethod
    def fingerprint_inputs(cls, **kwargs):
        unique_id = cls.hidden.unique_id
        node_id = str(unique_id)
        selections_for_node = cls.selections.get(node_id, {})
        timestamp = time.time()
        return f"{node_id}:{json.dumps(selections_for_node)}:{timestamp}"


@register_operation_handler
async def handle_csv_dropdown_operations(request):
    """Handle multi-dropdown operations via message route"""
    try:
        data = await request.json()
        operation = data.get('operation')
        if operation not in ['update_selections', 'remove_selection']:
            return None

        node_id = str(data.get('id', ''))
        payload = data.get('payload', {})

        if operation == 'update_selections':
            selections_for_node = {}
            entries_for_node = {}

            for key, value in payload.items():
                if key.endswith("_entries"):
                    dropdown_id = key[:-8]
                    entries_for_node[dropdown_id] = value
                else:
                    selections_for_node[key] = value

            if selections_for_node:
                DN_CSVMultiDropDownNode.selections[node_id] = selections_for_node
            if entries_for_node:
                DN_CSVMultiDropDownNode.entries_map[node_id] = entries_for_node

            return web.json_response({"status": "success"})

        elif operation == 'remove_selection':
            DN_CSVMultiDropDownNode.selections.pop(node_id, None)
            DN_CSVMultiDropDownNode.entries_map.pop(node_id, None)
            return web.json_response({"status": "success"})

        return web.json_response({"error": "Invalid operation or parameters"}, status=400)

    except json.JSONDecodeError:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)
