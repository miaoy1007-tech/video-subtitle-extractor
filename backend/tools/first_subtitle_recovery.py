"""Recover a subtitle already visible at the first frame using a short padded probe."""
import os
import subprocess
import tempfile
from pathlib import Path
import imageio_ffmpeg
import pysrt

PAD_MS = 2000
PROBE_SECONDS = 2

def recover_first_subtitle(video_path, output_path, run_probe, log=print):
    """Probe only if the normal SRT lacks a cue at the beginning.

    run_probe receives (video, srt); probe failures never replace the normal result.
    """
    output = Path(output_path)
    if not output.is_file():
        log('首句补检跳过：没有可用的字幕文件。')
        return False
    original = pysrt.open(str(output), encoding='utf-8')
    if original and original[0].start.ordinal <= 200:
        log('首句补检跳过：已有接近视频起点的字幕。')
        return False
    with tempfile.TemporaryDirectory(prefix='vse-first-') as tmp:
        probe_video = Path(tmp) / 'first.mp4'
        probe_srt = Path(tmp) / 'first.srt'
        command = [imageio_ffmpeg.get_ffmpeg_exe(), '-nostdin', '-v', 'error',
                   '-t', str(PROBE_SECONDS), '-i', str(video_path), '-an',
                   '-vf', 'tpad=start_duration=2:start_mode=add:color=black',
                   '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p',
                   '-y', str(probe_video)]
        result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        if result.returncode:
            log('首句补检未完成，保留原字幕：视频预处理失败。')
            return False
        run_probe(str(probe_video), str(probe_srt))
        if not probe_srt.is_file():
            log('首句补检未找到字幕，保留原结果。')
            return False
        probe = pysrt.open(str(probe_srt), encoding='utf-8')
        for cue in probe:
            start, end = cue.start.ordinal - PAD_MS, cue.end.ordinal - PAD_MS
            # Only accept text beginning at the source boundary; do not infer a missing mid-video cue.
            if not (-150 <= start <= 150 and end > 0 and cue.text.strip()):
                continue
            end = min(end, PROBE_SECONDS * 1000)
            if original and end > original[0].start.ordinal:
                log('首句补检结果与现有字幕重叠，未自动添加。')
                return False
            cue.start = pysrt.SubRipTime(milliseconds=0)
            cue.end = pysrt.SubRipTime(milliseconds=end)
            original.insert(0, cue)
            original.clean_indexes()
            temporary = output.with_name(output.name + '.first-recovery.tmp')
            try:
                original.save(str(temporary), encoding='utf-8')
                os.replace(temporary, output)
            finally:
                if temporary.exists():
                    temporary.unlink()
            log('首句补检：已补回视频开头字幕，请检查文字准确性。')
            return True
    log('首句补检未找到符合条件的字幕，保留原结果。')
    return False
