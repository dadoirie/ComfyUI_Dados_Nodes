from comfy_api.latest import io

class DN_MultilineString(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="DN_MultilineString",
            display_name="Multiline String",
            category="Dado's Nodes/Text & Prompt",
            description="A simple multiline string input node",
            inputs=[
                io.String.Input("text", multiline=True, default="")
            ],
            outputs=[
                io.String.Output()
            ]
        )

    @classmethod
    def execute(cls, text):
        return io.NodeOutput(text)