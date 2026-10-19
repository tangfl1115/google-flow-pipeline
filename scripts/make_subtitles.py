# Version: 1.0.0
# Changelog: Automated ASS Dual-Color Subtitle Generator with phased short-clause timing and keyword highlights

import os
import sys
import json
import re
from pathlib import Path
from typing import List, Dict

ASS_HEADER = """[Script Info]
Title: Google Flow Phased Subtitles
ScriptType: v4.00+
Collisions: Normal
PlayDepth: 0
Timer: 100.0000

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Microsoft JhengHei,40,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0.5,0,1,3.5,1,2,30,30,55,1
Style: HighlightYellow,Microsoft JhengHei,42,&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0.5,0,1,3.5,1,2,30,30,55,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

def format_ass_time(seconds: float) -> str:
    """Format seconds into ASS timestamp H:MM:SS.cc"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def highlight_keywords(text: str, keywords: List[str]) -> str:
    """Wrap keywords in ASS cyan or yellow color codes."""
    res = text
    for kw in sorted(keywords, key=len, reverse=True):
        if kw in res:
            res = res.replace(kw, f"{{\\c&H00FFFF&}}{kw}{{\\c&HFFFFFF&}}")
    return res

def generate_ass(storyboard_json: str, output_ass: str, keywords: List[str] = None):
    """Generate ASS subtitle file from storyboard JSON."""
    keywords = keywords or []
    with open(storyboard_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    shots = data.get("shots", [])
    intro_dur = data.get("intro_duration", 2.0)
    
    current_time = intro_dur
    dialogue_lines = []

    for shot in shots:
        dur = shot.get("duration", 10.0)
        lines = shot.get("subtitles", [])
        
        # If subtitles provided as single text or list
        if isinstance(lines, str):
            lines = [{"text": lines, "fraction": 1.0}]
        
        total_frac = sum(item.get("fraction", 1.0) for item in lines)
        shot_start = current_time
        
        for item in lines:
            text = item.get("text", "")
            frac = item.get("fraction", 1.0)
            sub_dur = dur * (frac / total_frac)
            sub_end = shot_start + sub_dur
            
            styled_text = highlight_keywords(text, keywords)
            t_start = format_ass_time(shot_start)
            t_end = format_ass_time(sub_end)
            
            dialogue_lines.append(f"Dialogue: 0,{t_start},{t_end},Default,,0,0,0,,{styled_text}")
            shot_start = sub_end
            
        current_time += dur

    with open(output_ass, "w", encoding="utf-8") as f:
        f.write(ASS_HEADER + "\n".join(dialogue_lines) + "\n")

    print(f"[Subtitles] Generated {len(dialogue_lines)} subtitle events -> {output_ass}")

if __name__ == "__main__":
    if len(sys.argv) > 2:
        generate_ass(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python make_subtitles.py <storyboard.json> <output.ass>")
