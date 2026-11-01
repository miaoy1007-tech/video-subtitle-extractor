#!/usr/bin/env python3
"""Provide an existing SRT to the local caption pipeline's OCR input boundary."""
import os
import shutil
import sys
from pathlib import Path

try:
    source = Path(os.environ['VSE_EXTERNAL_SRT'])
    output = Path(sys.argv[sys.argv.index('--output') + 1])
    if not source.is_file():
        raise ValueError('字幕文件不存在')
    shutil.copyfile(source, output)
except (KeyError, ValueError, IndexError, OSError) as exc:
    print(f'无法读取字幕文件: {exc}', file=sys.stderr)
    raise SystemExit(1)
