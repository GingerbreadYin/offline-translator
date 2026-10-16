# 离线框选翻译 · Offline Translator

Windows 11 英文阅读小工具。手动启动、常驻托盘，截图识别、词典和英译中模型全部在本机运行。v0.1.0 首版。

## 使用发行包

1. 解压完整 `OfflineTranslator-v0.1.0-win-x64.zip`，不要只复制exe。
2. 双击 `OfflineTranslator.exe`；设置窗口可以重新绑定三个快捷键。
3. 点击“保存并启用”或关闭设置窗口，程序继续常驻右下角托盘。
4. 默认按 `Ctrl+Alt+Q`，拖出矩形框选英文，松开鼠标自动识别并翻译。
5. 单词只显示一个义项及其词性；按 `Ctrl+Alt+Up` / `Ctrl+Alt+Down` 循环切换义项。
6. 再按 `Ctrl+Alt+Q` 或 `Esc` 关闭译文。右键托盘可打开设置或彻底退出。

也支持在设置中绑定F键、字母等单键；它们可能影响其他程序输入。系统保留键、占用键和不支持的按键会被拒绝。设置窗口打开期间暂停全局快捷键，避免录入冲突。

本版首次完整包已附带离线资源，解压即可使用；不会在日常翻译时下载模型或发送截图/文字。源代码构建需要首次联网下载资源。没有开机自启、翻译历史或云端功能。

## 释义与翻译

- 单词使用ECDICT默认义项顺序，不承诺默认义项最常见或最适合当前上下文。
- 短语和句子使用Argos提供的OPUS英译中模型，通过CTranslate2在CPU上运行。
- 缺词回退为文本翻译，不编造词性。代码反引号片段和显式URL尽量原样保留。
- 本版每次最多2000字符，推荐框选单词或短句。普通标识符和技术术语可能仍被翻译，不保证逐字符保持所有专业内容。

## 限制与故障处理

- 实测了清晰英文合成图片与示例短句；艺术字体漫画、小字号、复杂背景尚未做真实样本验收。
- 多屏可分别框选，第一版不支持横跨两块屏幕拖出同一个矩形。
- 部分受保护视频、特殊全屏界面可能无法截图。OCR和模型均可能出错，请以原文为准。
- 翻译基于轻量模型，输出不一定达到联网大模型效果。冷启动首次识别比后续慢。
- 框选时截图只在内存暂存；截图内容不会写入运行日志。应用配置位于 `%LOCALAPPDATA%\OfflineTranslator\settings.json`。
- 提示资源损坏时重新解压完整包；不要从不明来源替换模型。发生快捷键冲突时换一组按键。
- Windows可能提示此程序发布者未知，因为本版未购买代码签名证书。

## 从源码运行（Python 3.12 x64）

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe tools\prepare_resources.py --download
.\.venv\Scripts\python.exe main.py
```

资源准备脚本会先验证锁定的源文件SHA256，再导入词典、提取翻译所需文件。重新执行时不自动删除原文件。

## 测试与打包

```powershell
New-Item -ItemType Directory -Force build | Out-Null
.\.venv\Scripts\python.exe -m pytest -q --basetemp=build/test-temp
.\.venv\Scripts\python.exe main.py --self-test
.\.venv\Scripts\python.exe main.py --ui-smoke
.\.venv\Scripts\python.exe main.py --worker-test
powershell -ExecutionPolicy Bypass -File scripts\publish.ps1
```

`--self-test`验证资源校验和及真实OCR/翻译，不访问网络；输出使用合成英文样本。测试数据不会包含用户阅读内容。没有准备大模型时，相关模型集成测试会跳过，单元/界面测试仍可执行。

打包脚本还会检查最终exe的资源推理、独立推理进程与界面启动/退出，任一失败均不生成新的发行ZIP。

## 后续迭代

通过Git提交维护每次变更，使用`v0.1.0`、`v0.2.0`等标签标识版本。优先收集实际阅读中的识别、词义拆分和交互问题；联网翻译、词汇统计按后续需求逐步加入。

复用资源与许可证见 [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)，开发取舍见 [docs/progress.md](docs/progress.md)，实测输出见 [docs/probe-results.json](docs/probe-results.json)。
