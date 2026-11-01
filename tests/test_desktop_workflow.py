"""Offline checks for the desktop handoff; no downloads or paid API calls."""
import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import QProcess, QSettings
from PySide6.QtWidgets import QApplication, QWidget

from ui.caption_bridge_interface import CaptionBridgeInterface
from ui.home_interface import HomeInterface


class DesktopWorkflowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        QSettings.setDefaultFormat(QSettings.IniFormat)
        QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, cls.temp.name)
        cls.app = QApplication.instance() or QApplication([])

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_translation_handoff_preserves_video_subtitle_and_auto_choice(self):
        with tempfile.TemporaryDirectory() as d:
            video, subtitle = Path(d) / 'video.mp4', Path(d) / 'source.srt'
            video.touch()
            subtitle.touch()
            page = CaptionBridgeInterface()
            page.video.setText(str(video))
            page.subtitle.setText(str(subtitle))
            with patch.object(Path, 'is_file', return_value=True), patch.object(
                QProcess, 'startDetached', return_value=(True, 123)
            ) as start:
                page.auto_synthesize.setChecked(False)
                page.start()
                self.assertEqual(start.call_args.args[1], ['--review-ocr', str(video), str(subtitle)])
                page.auto_synthesize.setChecked(True)
                page.start()
                self.assertEqual(start.call_args.args[1][-1], '--auto-synthesize')
            page.close()

    def test_caption_handoff_returns_only_matching_video_without_changing_preferences(self):
        with tempfile.TemporaryDirectory() as d:
            video = Path(d) / 'video.mp4'
            subtitle = Path(d) / 'source.original.srt'
            response = Path(d) / 'ocr-result.json'
            video.touch()
            subtitle.write_text('original', encoding='utf-8')
            page = HomeInterface()
            try:
                page.workflow_settings.setValue("auto_translate", True)
                page.auto_translate.setChecked(True)
                page.configure_caption_handoff(str(video), str(response))
                self.assertTrue(page.workflow_settings.value('auto_translate', type=bool))
                self.assertFalse(page.auto_translate.isEnabled())
                page.send_caption_result('/wrong/video.mp4', str(subtitle))
                self.assertFalse(response.exists())
                page.send_caption_result(str(video), str(subtitle))
                self.assertEqual(json.loads(response.read_text()), {
                    'video': str(video.resolve()), 'subtitle': str(subtitle.resolve())
                })
                self.assertIsNone(page.caption_handoff)
            finally:
                page.close()

    def test_download_completion_imports_the_exact_result(self):
        with tempfile.TemporaryDirectory() as d:
            video = Path(d) / 'video.mp4'
            video.touch()
            page = HomeInterface()
            page.download_output = 'VIDEO_RESULT="' + str(video) + '"\n'
            with patch.object(page, 'read_download_output'), patch.object(
                page, 'import_video', return_value=True
            ) as imported:
                page.download_finished(0, QProcess.NormalExit)
                imported.assert_called_once_with(str(video))
            page.close()

    def test_ocr_completion_sends_original_files_to_translation(self):
        window = QWidget()
        window.captionBridgeInterface = CaptionBridgeInterface(window)
        window.switchTo = lambda page: None
        page = HomeInterface(window)
        with patch.object(window.captionBridgeInterface, 'start') as start:
            page.continue_to_translation('/tmp/source.mp4', '/tmp/source.srt')
            self.assertEqual(window.captionBridgeInterface.video.text(), '/tmp/source.mp4')
            self.assertEqual(window.captionBridgeInterface.subtitle.text(), '/tmp/source.srt')
            self.assertEqual(window.captionBridgeInterface.mode.currentData(), 'translate')
            start.assert_called_once_with()
        page.close()
        window.close()


if __name__ == '__main__':
    unittest.main()
