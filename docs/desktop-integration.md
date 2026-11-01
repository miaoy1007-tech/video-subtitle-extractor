# VideoCaptioner 联动

在提取器点击“下载视频”，使用 VideoCaptioner 的下载方式和 Cookie，下载成功后载入视频。框选画面字幕区域并选择语言，再点击“运行”。单任务默认在提取成功后自动送入 VideoCaptioner 翻译；可关闭“提取后自动翻译”。批量任务先完成提取，再选择一项点击“翻译与合成”。

“原文字幕 → 翻译 → 合成视频”先经过 OCR 质量检查。默认翻译完成后在 VideoCaptioner 检查、编辑，点击“保存并合成”；勾选“翻译完成后自动合成”可连续执行。两个选项记住上次选择。原视频画面中的硬字幕会保留。

原文字幕、视频和识别失败的文件不会被联动入口删除。视频和译文、成片按 VideoCaptioner 的设置保存。字幕提取器按本机配置调用 `/Users/miaoyu/Developer/VideoCaptioner`，VideoCaptioner 调用本机提取器的工作目录；移动项目时需要更新对应路径。
