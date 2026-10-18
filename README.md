# 七源投资晨晚报：2026-10-18 代码交接

这份交接包用于让同样使用 **MacBook** 的接手同事及其 Codex **从当前重建版本继续开发**。它尚未通过 Mac 定时任务端到端验收：现有 Python 代码能导入真实浏览器快照、核验阅读清单、制作 Mac 离线音频和检查交付条件，但不能在无人参与的定时运行中独立控制已登录浏览器并读完七源。Windows 原需求保留，实机测试按用户最新安排延后。请先读[当前需求](docs/current/CURRENT_REQUIREMENTS.md)、[编辑与采集规则](docs/current/SUMMARY_RULES.md)、[需求追踪](docs/REQUIREMENTS_TRACEABILITY.md)、[关键决策](docs/DECISIONS_AND_CONFLICTS.md)、[沟通记录](docs/COMMUNICATION_RECORD.md)、[实现状态](docs/IMPLEMENTATION_STATUS.md)和[待改事项](docs/OPEN_WORK.md)，再运行代码。旧交接材料仅供追溯；与用户后来明确指令冲突时，以当前需求为准。

## 目录

| 路径 | 用途 |
| --- | --- |
| `project/` | 当前可执行源码、单元测试及必要的无凭据文件；主要包为 `project/digest/` |
| `docs/current/` | 已合并本聊天后续变更的需求及 `SUMMARY_RULES.md` |
| `docs/IMPLEMENTATION_STATUS.md` | 已实现功能、证据等级与尚未通过的验收 |
| `docs/HANDOFF_ACCEPTANCE.md` | 独立解压、测试、依赖和 Mac 短音频的交接验收记录 |
| `docs/OPEN_WORK.md` | 接手后要补齐的工作及完成标准 |
| `legacy_reference/` | 2026-10-10 原交接材料、原设备规则与 source-reference；只作历史对照 |
| `config_examples/` | [配置说明](config_examples/README.md)及供接手者复制、填写的模板；不得把本机私有配置直接上传 |
| `CODEX_START_HERE.md`、`AGENTS.md` | [接手同事的 Codex 起始指引](CODEX_START_HERE.md)与开发原则 |
| `docs/AUTOMATION_CONTRACT.md` | 08:00／20:00 预处理和 09:00／21:00 交付的时点及迁移边界 |

包内不应包含浏览器 Cookie、令牌、登录配置、用户下载的研报原件、历史 `evidence/`、`tmp/`、`work/`、旧报告或音频。原始浏览器证据和最近的交付回执留在原机；本包通过状态文档记录其结论，不把缺失的证据称作已随包移交。团队若需核验第三方材料，应从各自获授权的来源重新取得。

## 当前口径

七源为四个指定知识星球和三个指定 X 账号，代码中的清单见 `project/digest/policy.py`。全部时间按北京时间：晨报覆盖前一日 21:00 至当日 09:00，晚报覆盖当日 09:00 至 21:00，起点包含、终点不包含。08:00／20:00 预处理先读取已发生的信息；09:00／21:00 复查最后一小时和整个窗口后才交付。源列表出现条目不等于正文、评论或附件已读。行情与八只持仓公告也要单独核验，公告来源为东方财富。报告与完整离线音频须逐项对应；清理只可在交付核验通过之后按用户授权执行。

## 运行前置与入口

- Python 3.10 或更新版本；`project/requirements.txt` 列出 `pypdf>=6.10,<7`，接手 MacBook 安装时须能访问获准的 Python 依赖源。ZIP 不捆绑依赖 wheel；本次受限环境访问 PyPI 的 DNS 失败，独立 venv 未完成依赖安装，详见 `docs/HANDOFF_ACCEPTANCE.md`。它是版本范围，不是精确锁定文件。PDF 页数校验在部分路径使用系统 `pdfinfo` 作为回退。
- Mac 音频使用本机 `/usr/bin/say` 和 `/usr/bin/afconvert`，并要求已安装离线音色 Tingting（中文）和 Samantha（英文）。外发包**不含** `project/mac_audio_config.json`；先按[配置说明](config_examples/README.md)复制 `config_examples/mac_audio_config.example.json`，再填写接手 MacBook 的本机绝对路径。音频输出盘须有至少 1 GiB 可用空间。Windows Yaoyao 仅保留为后续需求与常量，尚无可运行的 Windows 音频入口。
- `project/ocr_pdf_macos.swift` 使用 macOS 的 PDFKit、Vision、AppKit；这是需人工核对的 OCR 辅助工具，不能把 OCR 输出自动视作全文已读。
- 已登录的七源浏览器页面及对下载、使用附件的合法权限，由接手者在自己的环境准备。不要复制原机登录状态，不要修改安全设置或绕过站点/App 限制。

在交接包根目录创建隔离 Python 环境并运行测试；以下命令不会自行抓取七源：

```bash
cd project
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -q
.venv/bin/python collect_browser_snapshot.py --help
```

要在接手 MacBook 上实际生成音频，还必须先完成本机路径、声线与报告核对：

```bash
# 从交接包根目录执行
cp config_examples/mac_audio_config.example.json project/mac_audio_config.json
# 编辑 project/mac_audio_config.json，将占位用户名改为接手 MacBook 的实际本机路径
cd project
.venv/bin/python extract_downloaded_pdfs.py /absolute/path/to/authorized.pdf
.venv/bin/python render_report_audio_macos.py /absolute/path/to/verified-report.md
```

外发包在**未创建本机音频配置**时实测 `30 tests, OK (skipped=1)`；跳过的仅是依赖本机音频路径的配置测试。创建配置后应重新运行全部测试，并单独真实生成、核验完整音频。测试使用的模拟调用不能证明浏览器读取、音频播放或 Scheduled 成功。

`collect_browser_snapshot.py` 只导入由已登录浏览器真实导出的 JSON。预处理阶段要求 `--day`、`--edition`、`--source`、`--snapshot`、`--phase preparation` 和带时区的 `--prepared-at`；最终阶段用 `--phase final`，完整性提升还需逐条审读后的 `--review-manifest`。`digest/browser_review.py` 负责核对原生主题/帖子身份、评论和附件阅读证据；它不会代替浏览器打开内容。`digest/staging.py` 提供检查点和最终交付门槛，但目前没有将浏览器采集、行情、东方财富公告、写稿和音频贯通的独立命令行运行器。`audit_20261015.py` 为特定旧日期诊断脚本，不应当作每日入口。

原机存在依附**本聊天**的 Codex 心跳定时任务（北京时间 08:00、09:00、20:00、21:00），其状态曾为 `ACTIVE`。这项设置不在代码包内，也不能直接转移到同事的 Codex；不要仅凭“已启用”判定定时端到端成功。接手 MacBook 需另行建立任务并完成真实 Scheduled 运行验收。

## 接手顺序

1. 对照 `docs/current/` 与 `legacy_reference/` 理清需求优先级，逐项读取 `docs/IMPLEMENTATION_STATUS.md` 与 `docs/OPEN_WORK.md`。
2. 在隔离目录中配置本机路径、依赖和已授权的七源访问；运行单元测试。测试通过只证明代码行为，不能替代真实采集或实机验收。
3. 先完成一轮可审计的七源正文、网页可见评论及应读附件读取，再接通行情、东方财富八只证券公告、报告、HTML 和音频。
4. 优先验收接手 MacBook 的真实定时触发与整轮交付。Windows 并排部署及实机验收保留在待办清单，按用户最新安排延后。所有无法读取的项目保留明确缺口，不用旧证据或标题推测内容。

`MANIFEST.sha256` 可在解压后的交接包根目录用 `shasum -a 256 -c MANIFEST.sha256` 核对文件；`SOURCE_PROVENANCE.json` 标明与原机当前源码逐文件哈希的关系。只有一个测试文件为去除原机用户名硬编码而作交接适配，其余 22 个 Python/Swift 源文件字节一致。ZIP 不含 `.git` 历史；可在[公开 GitHub 仓库](https://github.com/Mickymousemickymouse/seven-source-investment-brief-handoff)查看和下载当前代码。用户已确认原样公开，包括包内的固定来源 ID、持仓证券代码和沟通摘要；隐私与排除范围见 `docs/SHARING_AND_EXCLUSIONS.md`。

这份 README 记录的是**2026-10-18 的代码状态**，不是对未来每期报告完整性的保证。每轮仍需用对应时间窗口的真实来源和阅读记录重新核验。
