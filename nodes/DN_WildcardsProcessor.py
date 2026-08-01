from dynamicprompts.generators import RandomPromptGenerator
from dynamicprompts.generators.attentiongenerator import AttentionGenerator
from comfy_api.latest import io

class DN_WildcardsProcessor(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="DN_WildcardsProcessor",
            display_name="Wildcards Processor",
            category="Dado's Nodes/Text & Prompt",
            description="Process text with wildcards using dynamic prompts",
            inputs=[
                io.String.Input("text", multiline=True, tooltip="Text with wildcards to process"),
                io.Int.Input("seed", default=0, min=0, max=0xFFFFFFFFFFFFFFFF, tooltip="Seed for wildcard randomization"),
                io.Boolean.Input("use_attention", default=False, tooltip="Use attention generator for emphasis")
            ],
            outputs=[
                io.String.Output(display_name="processed_text"),
                io.Int.Output(display_name="seed")
            ]
        )
    
    @classmethod
    def execute(cls, text, seed, use_attention):
        if not text:
            return (text, seed)
        
        generator = RandomPromptGenerator()
        
        if use_attention:
            attention_generator = AttentionGenerator(generator)
            prompts = attention_generator.generate(text, num_prompts=1, seeds=seed)
            
            fixed_prompts = []
            for prompt in prompts:
                import re
                fixed_prompt = re.sub(r'\((,\s*)', r'\1(', prompt)
                fixed_prompts.append(fixed_prompt)
            processed_text = fixed_prompts[0] if fixed_prompts else text
        else:
            prompts = generator.generate(text, num_images=1, seeds=seed)
            processed_text = list(prompts)[0] if prompts else text
        
        return io.NodeOutput(processed_text, seed)
    
    @classmethod
    def fingerprint_inputs(cls, **kwargs):
        return kwargs['seed']