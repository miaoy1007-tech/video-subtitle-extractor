"""Run the local Apple Vision subtitle extractor using the GUI's selected region."""
import json
import os
import subprocess
import tempfile
from pathlib import Path

import cv2
import pysrt

BINARY = Path.home() / '.local/bin/video-ocr-srt'
LANGUAGES = {
    'ch': 'zh-Hans', 'chinese_cht': 'zh-Hant', 'en': 'en-US', 'japan': 'ja-JP',
    'korean': 'ko-KR', 'ar': 'ar-SA', 'french': 'fr-FR', 'fr': 'fr-FR',
    'german': 'de-DE', 'de': 'de-DE', 'ru': 'ru-RU', 'es': 'es-ES',
    'pt': 'pt-BR', 'it': 'it-IT', 'cs': 'cs-CZ', 'da': 'da-DK',
    'fi': 'fi-FI', 'hi': 'hi-IN', 'id': 'id-ID', 'mr': 'mr-IN',
    'ms': 'ms-MY', 'nl': 'nl-NL', 'no': 'no-NO', 'pl': 'pl-PL',
    'ro': 'ro-RO', 'sv': 'sv-SE', 'th': 'th-TH', 'tr': 'tr-TR',
    'uk': 'uk-UA', 'vi': 'vi-VT',
}

def extract(video, output, area, language, generate_txt=False, log=print, manage_pid=lambda pid: None):
    if not BINARY.is_file() or not os.access(BINARY, os.X_OK):
        raise RuntimeError(f'找不到本机 Apple Vision 工具：{BINARY}')
    lang = LANGUAGES.get(language)
    if not lang:
        raise ValueError(f'Apple Vision 暂不支持当前选择的字幕语言：{language}。请选择支持的语言或其他识别模式。')
    if area is None:
        raise ValueError('请先框选字幕区域。')
    if getattr(area, 'ab_section', None) is not None:
        raise ValueError('Apple Vision 模式暂不支持绑定到时间分段的选区，请使用普通选区。')
    cap = cv2.VideoCapture(str(video))
    try:
        width, height = cap.get(cv2.CAP_PROP_FRAME_WIDTH), cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    finally:
        cap.release()
    if width <= 0 or height <= 0:
        raise ValueError('无法读取视频尺寸。')
    x0, x1 = sorted((float(area.xmin), float(area.xmax)))
    y0, y1 = sorted((float(area.ymin), float(area.ymax)))
    if x0 < 0 or y0 < 0 or x1 > width or y1 > height or x0 == x1 or y0 == y1:
        raise ValueError('字幕区域无效或超出视频画面。')
    roi = f'{x0/width:.8f},{y0/height:.8f},{(x1-x0)/width:.8f},{(y1-y0)/height:.8f}'
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.apple-ocr-', dir=str(output.parent)) as tmp:
        staged = Path(tmp) / 'subtitle.srt'
        cmd = [str(BINARY), str(Path(video).resolve()), '--roi', roi, '--lang', lang,
               '--output', str(staged), '--json']
        log(f'Apple Vision 本机识别：语言 {lang}，字幕区域 {roi}。')
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
        manage_pid(process.pid)
        stdout, stderr = process.communicate()
        if process.returncode:
            try:
                error = json.loads(stdout).get('message', '')
            except (ValueError, AttributeError):
                error = ''
            raise RuntimeError(f'Apple Vision 识别失败（{process.returncode}）：{error or stderr.strip() or "未知错误"}')
        if not staged.is_file():
            raise RuntimeError('Apple Vision 没有生成字幕文件。')
        cues = pysrt.open(str(staged), encoding='utf-8')
        if not cues:
            raise RuntimeError('Apple Vision 未找到字幕。')
        os.replace(staged, output)
        if generate_txt:
            txt = output.with_suffix('.txt')
            txt.write_text(''.join(c.text + '\n' for c in cues), encoding='utf-8')
        try:
            result = json.loads(stdout)
            elapsed = result.get('elapsed_seconds')
        except (ValueError, AttributeError):
            elapsed = None
        log(f'Apple Vision 完成：{len(cues)} 条字幕' + (f'，耗时 {elapsed:.1f} 秒' if isinstance(elapsed, (int, float)) else '') + f'。\n字幕文件：{output}')
