# 离线框选翻译 · Offline Translator

Windows 11 英文阅读小工具。手动启动、常驻托盘，截图识别、词典和英译中模型全部在本机运行。当前版本 v0.1.2。

## 使用发行包

1. 升级前先在托盘退出旧版，然后解压完整 `OfflineTranslator-v0.1.2-win-x64.zip`，不要只复制exe。
2. 双击 `OfflineTranslator.exe`；设置窗口可以重新绑定六个快捷键。
3. 点击“保存快捷键”或关闭设置窗口，程序继续常驻右下角托盘。
4. 默认按 `CapsLock`，拖出矩形框选英文，松开鼠标自动识别并翻译。
5. 单词只显示一个义项及其词性；按逗号键 `,` / 句号键 `.` 循环切换上一个／下一个义项。
6. 再按 `CapsLock` 或 `Esc` 关闭译文。
7. `Ctrl+Q` 暂停／恢复软件功能。暂停时关闭当前框选与译文，释放另外五个快捷键；开关键继续有效。托盘也可以切换启用状态或彻底退出。

每次启动默认启用。暂停不会退出软件，旧任务结果不会在暂停后重新弹出。原有模型保留在后台供恢复时使用。暂停后可正常使用逗号、句号和CapsLock。

升级保留原有自定义快捷键，并补充全屏与收藏键；如果新增默认键与旧自定义键相同，会选择备用组合，请在设置中查看。

也支持在设置中绑定F键、字母等单键；它们可能影响其他程序输入。系统保留键、占用键和不支持的按键会被拒绝。设置窗口打开期间暂停全局快捷键，避免录入冲突。

本版首次完整包已附带离线资源，解压即可使用；不会在日常翻译时下载模型或发送截图/文字。源代码构建需要首次联网下载资源。没有开机自启或云端功能；仅主动收藏时保存文字。

## 全屏翻译与收藏

- 先点击想阅读的窗口，再按 `Ctrl+Shift+A`，翻译该窗口当前可见的英文。再次按同一快捷键或 Esc 关闭。
- 页面保持稳定约0.65秒后提交识别。滚动或画面变化会隐藏旧译文，稳定后重新识别，未变化的文字复用译文。响应时间取决于文字量和电脑性能。
- 译文优先放在原文上方；空间不足时在屏幕旁边显示编号译文栏。窗口最大化时，旁栏可能覆盖右侧部分内容；可缩小原窗口留出位置。旁栏可滚动，原文上方的覆盖层不拦截鼠标。
- 切换到其他窗口时隐藏译文；回到原窗口后重新检查。目标窗口关闭或最小化时停止，可重新按快捷键开启。
- `Ctrl+Shift+S` 收藏：全屏模式先把鼠标移到需要的译文（或旁栏条目）上再按键，只保存这一条；框选模式直接保存本次全部原文及当前译文/义项。
- 托盘右键 → “收藏列表”查看英文、中文和收藏时间，选中条目可删除。相同原文不会重复，选择不同义项再次收藏会更新已有译文和时间。
- 收藏数据库：`%LOCALAPPDATA%\OfflineTranslator\favorites.db`。升级可执行程序不会删除收藏；不保存截图，不自动保存未收藏的翻译。
- Ctrl+Shift+A、Ctrl+Shift+S 可能覆盖浏览器等程序的原快捷键，可在设置修改。暂停后释放，恢复其他软件使用。

## 释义与翻译

- 单词使用ECDICT默认义项顺序，不承诺默认义项最常见或最适合当前上下文。
- 短语和句子使用Argos提供的OPUS英译中模型，通过CTranslate2在CPU上运行。
- 缺词回退为文本翻译，不编造词性。代码反引号片段和显式URL尽量原样保留。
- 框选每次最多2000字符；全屏按不超过约1800字符的段落分别翻译。普通标识符和技术术语可能仍被翻译，不保证逐字符保持所有专业内容。

## 限制与故障处理

- 实测了清晰英文合成图片与示例短句；艺术字体漫画、小字号、复杂背景尚未做真实样本验收。
- 多屏可分别框选；不支持横跨两块屏幕的同一个框选矩形。全屏翻译优先目标窗口所在显示器，跨屏窗口仅显示该屏内完整段落。
- 正文筛选依赖截图启发式，无法像浏览器扩展一样准确理解网页结构，可能漏掉小字或把部分控件当正文。动态视频、闪烁光标和持续动画可能推迟稳定检测。
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
.\.venv\Scripts\python.exe main.py --capture-test
.\.venv\Scripts\python.exe main.py --window-test
powershell -ExecutionPolicy Bypass -File scripts\publish.ps1
```

`--self-test`验证资源校验和及真实OCR/翻译，不访问网络；输出使用合成英文样本。测试数据不会包含用户阅读内容。没有准备大模型时，相关模型集成测试会跳过，单元/界面测试仍可执行。

打包脚本还会检查最终exe的资源推理、独立推理进程、界面启动/退出、受控窗口捕获与全屏翻译/收藏/更新流程，任一失败均不生成新的发行ZIP。

## 后续迭代

通过Git提交维护每次变更，使用`v0.1.0`、`v0.2.0`等标签标识版本。优先收集实际阅读中的识别、词义拆分和交互问题；联网翻译、词汇统计按后续需求逐步加入。

复用资源与许可证见 [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)，开发取舍见 [docs/progress.md](docs/progress.md)，实测输出见 [docs/probe-results.json](docs/probe-results.json)。
