# 实现与验收状态（截至 2026-10-18）

本表区分“代码已写”“单元测试通过”“原机手动交付”“真实 Scheduled／实机验收”。接手同事也使用 MacBook，**先完成 Mac 端**；Windows 需求保留，实机测试按用户最新安排延后。原项目曾被外部删除；本包为根据原交接材料与聊天中的后续要求**部分重建**的版本，不能声称找回或恢复了被删的完整旧源码。

| 范围 | 现有实现 | 证据与边界 |
| --- | --- | --- |
| 七源和报告窗口 | `project/digest/policy.py` 定义四个星球、三个 X、北京时间 09:00／21:00 窗口、八个持仓代码和报告检查 | 单元测试覆盖边界；每轮是否读全须另查真实证据 |
| 浏览器清单导入 | `collect_browser_snapshot.py`、`digest/browser_bridge.py` 能把真实浏览器 JSON 快照与哈希存入检查点 | Python 进程**不能独立控制已登录 Chrome**；清单导入始终是部分证据，不证明正文、评论或附件已读 |
| 逐条阅读核验 | `digest/browser_review.py` 核对原生链接、可见评论、附件文件哈希、PDF 页数与逐页笔记等 | 需要人/agent 先用获授权的浏览器实际打开并写审读清单；校验器不会产生阅读事实。网页不提供评论后台总数/原始 ID 时，仅按用户批准的网页可见范围和标明的本地去重 ID 处理 |
| 预处理与最终门槛 | `digest/staging.py` 保存 08:00／20:00 检查点，要求 09:00／21:00 后七源刷新、旧主题评论/附件复查、报告与音频哈希匹配 | 这是验证逻辑，不是完整调度或七源抓取器；缺少一条可独立跑通全链路的正式入口 |
| PDF、HTML 与 Mac 音频 | `digest/pdf_read.py`、`digest/html_report.py`、`digest/audio.py` 及相应入口已存在 | PDF 文字提取后仍要核对图表/扫描页；Mac Tingting/Samantha 曾实跑出可播放 WAV，并有报告正文输入哈希、格式/时长/文件哈希检查；不能据此推出每期都完成 |
| 行情与八证券公告 | 用户规则、八代码和历史手动核查记录存在 | 当前项目没有可重复、无人参与的东方财富八股公告采集与全市场复盘自动接线；每期需真实核对 |
| Windows（延后） | 需求保留 D 盘默认业务目录、旧项目并排部署及 Yaoyao | 当前重建代码没有 Windows 可运行音频/正式运行入口；用户已指示先不用安排 Windows 实机测试，仍不得声称通过 |
| 测试 | 在原机完整项目目录执行 30 项通过；在外发包未配置音频路径时执行 `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -q`，`30 tests, OK (skipped=1)` | 跳过的是本机路径配置测试；包内 `project/requirements.txt` 已列 `pypdf` 版本范围。单元测试既非真实网页七源覆盖，也非 Scheduled 验收 |

## 近次真实运行记录的结论

| 时间与版本 | 结果 | 不应误读为 |
| --- | --- | --- |
| 2026-10-15 21:00 晚报 | 用户批准原计划超时后**同一轮手动延时补读**。原机保有报告、来源/附件阅读记录及约 631.73 秒的 Mac 离线音频回执 | 原 Scheduled 成功；恢复了被删旧程序 |
| 2026-10-17 21:00 Scheduled | 原机状态记录为 `incomplete_access_block`：四星球只见公开预览，X 也不完整；该轮无合格报告和音频 | “自动化已启用”即等于该轮交付成功 |
| 2026-10-18 09:00 晨报 | **manual_delayed** 手动补读交付；原机交付记录明示 `scheduled_end_to_end_verified=false`。三份仅知识星球 App 可看的 DOCX 正文未读，按用户规则标注跳过；X 转发按原帖时间归窗 | 09:00 Scheduled 端到端已验收，或三份 DOCX 已读 |
| 2026-10-18 20:00 晚报预处理 | 截至本交接包制作时，用户要求先停下今晚人工整理、说明程序实际能力并准备代码交接；本轮尚未完成七源评论/附件及 21:00 交付核验 | 预处理检查过部分页面就等于今晚完整晚报已完成 |

上述运行记录的原始网页、研报、下载附件、报告/音频及完整回执**因个人信息、账号权限和第三方资料授权，不在外发交接包**。这些结论依据原机的 `RECOVERY_STATUS.md`、各轮状态 JSON 与交付回执整理；同事不能用本表替代新环境的实测。原机 2026-10-18 晨报回执位于 `outputs/investment-brief/outputs/investment-inbox/reports/2026-10-18-0900-late-delivery.json`，10月17日晚间状态位于 `outputs/investment-brief/work/2026-10-17-2100-scheduled-status.json`，原机恢复说明位于 `outputs/investment-brief/RECOVERY_STATUS.md`。这些路径仅供原机定位，不代表文件随包附带。

## 已知环境依赖与限制

- 源码使用 Python 3.10+ 语法；包内 `project/requirements.txt` 写明 `pypdf>=6.10,<7`，但不是精确锁定文件。`pdfinfo` 用于部分 PDF 页数校验回退。
- Mac TTS 依赖本地 Tingting/Samantha、系统 `say`/`afconvert` 与至少 1 GiB 可用空间；外发包不含原机 `project/mac_audio_config.json`，接手 MacBook 应根据 `config_examples/mac_audio_config.example.json` 新建本机绝对路径配置。缺少该配置时，单元测试中对应测试会跳过。
- `ocr_pdf_macos.swift` 仅适用于 macOS。Windows Yaoyao 的可运行实现与 Windows 实机验收仍是缺口，依用户最新安排延后。
- Codex 心跳定时任务配置在原机 Codex 环境、并依附本聊天，不在项目源码内；外发包不包含可直接迁移的登录状态或定时任务实例。
