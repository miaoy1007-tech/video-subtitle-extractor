"""Small interface for the existing VideoCaptioner pipeline."""
import sys
from pathlib import Path
from PySide6.QtCore import QProcess, QSettings
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog, QComboBox, QLineEdit, QCheckBox
from qfluentwidgets import PushButton, PlainTextEdit

class CaptionBridgeInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.finished.connect(self.finished)
        self.process.errorOccurred.connect(self.process_error)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.addWidget(QLabel('选择原视频和处理方式。翻译、字幕样式及 ASR 引擎使用 VideoCaptioner 中已有的设置。'))
        self.video = self.file_row(layout, '原视频', '选择视频', '视频文件 (*.*)')
        self.subtitle = self.file_row(layout, '字幕文件', '选择字幕', '字幕文件 (*.srt *.txt);;所有文件 (*)')
        layout.addWidget(QLabel('处理方式'))
        self.mode = QComboBox()
        self.mode.addItem('原文字幕 → 翻译 → 检查 → 合成视频', 'translate')
        self.mode.addItem('已有字幕 → 直接合成视频', 'render')
        self.mode.addItem('语音识别 → 翻译 → 合成视频', 'asr')
        self.mode.currentIndexChanged.connect(self.mode_changed)
        layout.addWidget(self.mode)
        self.workflow_settings = QSettings('miaoyu', 'SubtitleExtractorWorkflow')
        self.auto_synthesize = QCheckBox('翻译完成后自动合成', self)
        self.auto_synthesize.setChecked(self.workflow_settings.value('auto_synthesize', False, type=bool))
        self.auto_synthesize.toggled.connect(lambda value: self.workflow_settings.setValue('auto_synthesize', value))
        layout.addWidget(self.auto_synthesize)
        layout.addWidget(QLabel('直接合成使用所选字幕原文；合成后原有画面字幕仍会保留。'))
        self.run_button = PushButton('开始处理')
        self.run_button.clicked.connect(self.start)
        layout.addWidget(self.run_button)
        self.log = PlainTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log, 1)
        self.mode_changed()

    def file_row(self, layout, label, button_text, file_filter):
        layout.addWidget(QLabel(label))
        row = QHBoxLayout()
        field = QLineEdit()
        field.setPlaceholderText('请选择文件')
        button = PushButton(button_text)
        def choose():
            path, _ = QFileDialog.getOpenFileName(self, button_text, '', file_filter)
            if path:
                field.setText(path)
        button.clicked.connect(choose)
        row.addWidget(field, 1)
        row.addWidget(button)
        layout.addLayout(row)
        if label == '字幕文件':
            self.subtitle_button = button
        return field

    def mode_changed(self):
        needed = self.mode.currentData() != 'asr'
        self.subtitle.setEnabled(needed)
        self.subtitle_button.setEnabled(needed)
        self.auto_synthesize.setEnabled(self.mode.currentData() == 'translate')

    def start(self):
        if self.process.state() != QProcess.NotRunning:
            return
        video = self.video.text().strip()
        subtitle = self.subtitle.text().strip()
        mode = self.mode.currentData()
        if not Path(video).is_file() or (mode != 'asr' and not Path(subtitle).is_file()):
            self.log.appendPlainText('请先选择存在的视频和所需字幕文件。')
            return
        if mode == 'translate':
            root = Path('/Users/miaoyu/Developer/VideoCaptioner')
            program = root / '.venv/bin/videocaptioner-gui'
            if not program.is_file():
                self.log.appendPlainText('找不到 VideoCaptioner，请检查安装。')
                return
            args = ['--review-ocr', video, subtitle]
            if self.auto_synthesize.isChecked():
                args.append('--auto-synthesize')
            started, _ = QProcess.startDetached(str(program), args, str(root))
            self.log.appendPlainText('已发送到 VideoCaptioner。' if started else '无法启动 VideoCaptioner。')
            return
        bridge = Path(__file__).resolve().parents[1] / 'backend/tools/caption_bridge.py'
        args = [str(bridge), '--video', video, '--mode', mode]
        if mode != 'asr':
            args += ['--subtitle', subtitle]
        self.log.clear()
        self.run_button.setEnabled(False)
        self.process.start(sys.executable, args)
        if not self.process.waitForStarted(3000):
            self.log.appendPlainText('无法启动 VideoCaptioner。')
            self.run_button.setEnabled(True)

    def process_error(self, error):
        self.log.appendPlainText('启动或运行出错：' + self.process.errorString())
        self.run_button.setEnabled(True)

    def read_output(self):
        data = bytes(self.process.readAllStandardOutput()).decode('utf-8', errors='replace')
        cursor = self.log.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(data)
        self.log.setTextCursor(cursor)
        self.log.ensureCursorVisible()

    def finished(self, exit_code, exit_status):
        self.read_output()
        self.log.appendPlainText('处理完成。' if exit_code == 0 else f'处理未完成（退出码 {exit_code}），请查看上方日志。')
        self.run_button.setEnabled(True)
