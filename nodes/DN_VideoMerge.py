import os
import subprocess
import folder_paths
from comfy_api.latest import io


class DN_VideoMerge(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="DN_VideoMerge",
            display_name="Video Merge",
            category="Dado's Nodes/Video",
            description="Merge two mp4 videos, dropping the first frame of the second to avoid a duplicated frame",
            inputs=[
                io.String.Input("mp4_path_1", force_input=True),
                io.String.Input("mp4_path_2", force_input=True),
            ],
            outputs=[
                io.String.Output(display_name="mp4_path"),
            ],
        )

    @classmethod
    def execute(cls, mp4_path_1, mp4_path_2):
        if not mp4_path_1 or not os.path.isfile(mp4_path_1):
            raise ValueError(f"mp4_path_1 does not exist: {mp4_path_1}")
        if not mp4_path_2 or not os.path.isfile(mp4_path_2):
            raise ValueError(f"mp4_path_2 does not exist: {mp4_path_2}")

        output_dir = folder_paths.get_temp_directory()
        filename_prefix = "ComfyUI_merged"
        full_output_folder, filename, counter, _, filename_prefix = folder_paths.get_save_image_path(filename_prefix, output_dir)
        output_path = os.path.join(full_output_folder, f"{filename}_{counter:05}_.mp4")

        command = [
            "ffmpeg", "-y",
            "-i", mp4_path_1,
            "-i", mp4_path_2,
            "-filter_complex",
            "[1:v]select='gte(n\\,1)',setpts=PTS-STARTPTS[v1trimmed];[0:v][v1trimmed]concat=n=2:v=1:a=0[outv]",
            "-map", "[outv]",
            output_path,
        ]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8", check=False)
        if not os.path.isfile(output_path):
            raise ValueError(f"Failed to merge videos: {result.stderr}")

        return io.NodeOutput(output_path)