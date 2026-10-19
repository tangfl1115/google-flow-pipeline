# Version: 1.0.0
# Changelog: Zero-GPU CPU FFmpeg Master Video Assembler (Concat + 2.0s Cover Intro + Subtitles + Watermark Badge)

import os
import sys
import glob
import subprocess
from pathlib import Path

def assemble_master(
    clips_dir: str,
    cover_image: str,
    subtitles_ass: str,
    output_mp4: str,
    badge_image: str = None,
    intro_duration: float = 2.0
):
    """
    Concatenate video clips with intro cover, burn ASS subtitles, and apply channel watermark.
    """
    clips_path = Path(clips_dir).resolve()
    cover_path = Path(cover_image).resolve() if cover_image else None
    sub_path = Path(subtitles_ass).resolve() if subtitles_ass else None
    out_path = Path(output_mp4).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Gather all shot MP4 files in numerical / alphabetical order
    mp4_files = sorted(list(clips_path.glob("*.mp4")))
    if not mp4_files:
        raise FileNotFoundError(f"No MP4 clips found in {clips_dir}")

    print(f"[Assembler] Found {len(mp4_files)} clips to concatenate.")

    # 2. Generate 2.0s intro from cover image if provided
    temp_intro = out_path.parent / "_temp_intro.mp4"
    concat_list = out_path.parent / "_concat_list.txt"

    with open(concat_list, "w", encoding="utf-8") as f:
        if cover_path and cover_path.exists():
            print(f"[Assembler] Generating {intro_duration}s intro from cover plate...")
            cmd_intro = [
                "ffmpeg", "-y", "-loop", "1", "-i", str(cover_path),
                "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                "-c:v", "libx264", "-t", str(intro_duration), "-pix_fmt", "yuv420p", "-r", "30",
                "-c:a", "aac", "-b:a", "192k", "-shortest", str(temp_intro)
            ]
            subprocess.run(cmd_intro, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            f.write(f"file '{temp_intro.as_posix()}'\n")

        for clip in mp4_files:
            f.write(f"file '{clip.as_posix()}'\n")

    # 3. Build FFmpeg command with filter complex for overlay + subtitles
    inputs = ["-f", "concat", "-safe", "0", "-i", str(concat_list)]
    filter_chains = []
    current_stream = "0:v"

    # Logo watermark
    if badge_image and Path(badge_image).exists():
        inputs.extend(["-i", str(Path(badge_image).resolve())])
        badge_filter = f"[{current_stream}][1:v] overlay=36:28:enable='gte(t,{intro_duration})' [v_badge]"
        filter_chains.append(badge_filter)
        current_stream = "v_badge"

    # Subtitles burn-in
    if sub_path and sub_path.exists():
        escaped_sub = str(sub_path).replace("\\", "/").replace(":", "\\:")
        sub_filter = f"[{current_stream}] subtitles='{escaped_sub}' [v_final]"
        filter_chains.append(sub_filter)
        current_stream = "v_final"

    cmd_assemble = ["ffmpeg", "-y"] + inputs
    if filter_chains:
        cmd_assemble.extend(["-filter_complex", "; ".join(filter_chains), "-map", f"[{current_stream}]", "-map", "0:a"])
    else:
        cmd_assemble.extend(["-map", "0:v", "-map", "0:a"])

    cmd_assemble.extend([
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k",
        str(out_path)
    ])

    print("[Assembler] Running FFmpeg concatenation and mastering...")
    subprocess.run(cmd_assemble, check=True)
    print(f"[Assembler SUCCESS] Final master exported to:\n-> {out_path}")

    # Cleanup temporary files
    if temp_intro.exists():
        temp_intro.unlink(missing_ok=True)
    if concat_list.exists():
        concat_list.unlink(missing_ok=True)

if __name__ == "__main__":
    if len(sys.argv) > 4:
        assemble_master(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        print("Usage: python assemble_video.py <clips_dir> <cover.jpg> <subtitles.ass> <output.mp4> [badge.png]")
