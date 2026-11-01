#!/usr/bin/env python3
"""Run the existing VideoCaptioner workflow without modifying its input files."""
import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path('/Users/miaoyu/Developer/VideoCaptioner')
PIPELINE = ROOT / 'scripts/caption-one.sh'
ADAPTER = Path(__file__).with_name('external_srt_adapter.py')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--video', required=True)
    parser.add_argument('--subtitle')
    parser.add_argument('--mode', choices=('translate', 'render', 'asr'), required=True)
    args = parser.parse_args()
    video = Path(args.video).expanduser().resolve()
    if not video.is_file():
        parser.error('视频文件不存在')
    if not PIPELINE.is_file():
        parser.error('找不到 VideoCaptioner 工作流')
    env = os.environ.copy()
    if 'DOWNLOAD_ROOT' not in env:
        export_root = Path.home() / 'Library/Mobile Documents/com~apple~CloudDocs/MeTube-Downloads'
        for key, folder in [('DONE_DIR', 'caption-done'), ('REVIEW_DIR', 'caption-review'),
                            ('LOG_ROOT', 'caption-logs'), ('SUBTITLE_DIR', 'caption-txt')]:
            env.setdefault(key, str(export_root / folder))
    # The existing pipeline supports deleting or moving inputs; this bridge must never do either.
    env['DELETE_SOURCE_AFTER_SUCCESS'] = '0'
    env['MOVE_SOURCE_AFTER_SUCCESS'] = '0'
    command = ['bash', str(PIPELINE), str(video)]
    if args.mode in ('translate', 'render'):
        if not args.subtitle:
            parser.error('请选择字幕文件')
        subtitle = Path(args.subtitle).expanduser().resolve()
        if not subtitle.is_file():
            parser.error('字幕文件不存在')
        if args.mode == 'render':
            command += ['--subtitle', str(subtitle)]
        else:
            env['VIDEO_OCR_SRT_BIN'] = str(ADAPTER)
            env['VSE_EXTERNAL_SRT'] = str(subtitle)
            command += ['--source-mode', 'ocr', '--ocr-roi', '0,0,1,1', '--ocr-lang', 'external-srt']
    else:
        command += ['--source-mode', 'asr']
    print('正在调用 VideoCaptioner；原视频和原字幕会保留。', flush=True)
    return subprocess.run(command, env=env).returncode

if __name__ == '__main__':
    sys.exit(main())
