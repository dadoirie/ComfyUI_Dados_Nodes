from urllib.parse import urlparse
from comfy_api.latest import io
import requests

class DN_PythonCode(io.ComfyNode):
    _generation_dict = {"count": 0}
    _sandbox_template0 = '''\
import random
import re
import json
import numpy as np

def _string_function(a, b, c, seed):
'''

    _sandbox_template1 = '''\
_result.append(_string_function(_a, _b, _c, _seed))
'''

    ALLOWED_HOSTS = {"api.naga.ac"}
    
    @classmethod
    def _safe_request(cls, method, url, **kwargs):        
        p = urlparse(url)
        host = p.hostname

        if host is None:
            raise ValueError("Invalid URL")

        if host not in cls.ALLOWED_HOSTS:
            raise ValueError(f"Blocked host: {host}")

        kwargs["allow_redirects"] = False

        if 'timeout' not in kwargs:
            kwargs['timeout'] = 300
        return requests.request(method, url, **kwargs)

    @classmethod
    def safe_get(cls, url, **kw):
        return cls._safe_request("get", url, **kw)

    @classmethod
    def safe_post(cls, url, **kw):
        return cls._safe_request("post", url, **kw)

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="DN_PythonCode",
            display_name="Python String Function",
            category="Dado's Nodes/Utils",
            description="Execute Python code in a sandboxed environment with optional string parameters",
            inputs=[
                io.String.Input(
                    "python_code",
                    multiline=True,
                    default="return \"a text\"",
                    tooltip="Python code to execute (imports not allowed for security)"
                ),
                io.String.Input(
                    "a",
                    optional=True,
                    force_input=True,
                    tooltip="Optional string parameter a"
                ),
                io.String.Input(
                    "b",
                    optional=True,
                    force_input=True,
                    tooltip="Optional string parameter b"
                ),
                io.String.Input(
                    "c",
                    optional=True,
                    force_input=True,
                    tooltip="Optional string parameter c"
                ),
                io.Int.Input("seed", default=0, min=0, max=0xFFFFFFFFFFFFFFFF, tooltip="Seed for wildcard randomization"),
            ],
            outputs=[
                io.String.Output(display_name="output")
            ]
        )

    @classmethod
    def execute(cls, python_code, seed, a="", b="", c=""):
        if "import" in python_code:
            raise ValueError("\"import\" cannot be included in python_code for security reasons")

        python_code = python_code.replace("\\{", "{")
        python_code = python_code.replace("\\}", "}")

        code = (cls._sandbox_template0 +
                "    " + "\n    ".join((python_code + "\n").split("\n")) + "\n" +
                cls._sandbox_template1)

        sandbox_builtins = {k: v for k, v in __builtins__.items() if k not in ["eval", "exec"]}
        
        result = []
        exec(code, {
            "__builtins__": sandbox_builtins,
            "safe_get": cls.safe_get,
            "safe_post": cls.safe_post,
            "_result": result,
            "_seed": seed,
            "_a": a,
            "_b": b,
            "_c": c
        })
        
        return io.NodeOutput(str(result[0]) if result else "")
        
    @classmethod
    def fingerprint_inputs(cls, **kwargs):
        return kwargs['seed']
    #@classmethod
    #def fingerprint_inputs(cls, **kwargs):
        #cls._generation_dict["count"] += 1
        #return str(cls._generation_dict["count"])
