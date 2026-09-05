from comfy_api.latest import io
from ..deepseek_api.deepseek import DeepSeekClient


class DN_DeepSeekChat(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="DN_DeepSeekChat",
            display_name="DeepSeek Chat",
            category="Dado's Nodes/LLM",
            description="Chat with DeepSeek models. Outputs response and conversation_id.",
            inputs=[
                io.String.Input(
                    "prompt",
                    multiline=True,
                    default="Hello!",
                    tooltip="Your prompt to send to DeepSeek."
                ),
                io.String.Input(
                    "conversation_id",
                    default="",
                    tooltip="Optional: existing conversation_id to continue a multi‑turn chat."
                ),
                io.Combo.Input(
                    "model",
                    default="deepseek-chat",
                    options=["deepseek-chat", "deepseek-reasoner"],
                    tooltip="Model to use (only for first turn, when conversation_id is empty)."
                ),
                io.Boolean.Input(
                    "thinking",
                    default=False,
                    tooltip="Enable DeepThink reasoning mode."
                ),
                io.Boolean.Input(
                    "search",
                    default=False,
                    tooltip="Enable web search."
                ),
            ],
            outputs=[
                io.String.Output(display_name="response", tooltip="The complete response from DeepSeek."),
                io.String.Output(display_name="conversation_id", tooltip="ID for continuing this conversation."),
            ]
        )

    @classmethod
    def execute(cls, prompt, conversation_id, model, thinking, search):
        client = DeepSeekClient()

        # Build kwargs – only pass model if conversation_id is empty
        kwargs = {}
        if conversation_id:
            kwargs["conversation_id"] = conversation_id
        else:
            kwargs["model"] = model
        if thinking:
            kwargs["thinking"] = True
        if search:
            kwargs["search"] = True

        reply = client.chat(prompt, **kwargs)
        return io.NodeOutput(reply.text, reply.conversation_id)