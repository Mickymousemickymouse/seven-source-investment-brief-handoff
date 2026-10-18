# 交接包独立验收记录（2026-10-18）

本记录检验的是**当前版本能否完整交给另一台 MacBook 上的 Codex 继续开发**，不是七源自动晨晚报的生产验收。接手者应先读 `README.md`、`CODEX_START_HERE.md` 和 `docs/OPEN_WORK.md`，不得把下列测试结果写成真实来源或定时任务已验收。

| 检查 | 本次结果 | 仍需在接手 MacBook 完成 |
| --- | --- | --- |
| 交接包结构与完整性 | ZIP 可独立解压；全部文件的 `MANIFEST.sha256` 校验通过；无指向包外的符号链接 | 下载后再次运行 `shasum -a 256 -c MANIFEST.sha256` |
| 代码与规则移交 | 当前保存的 23 个 Python/Swift 源码及测试文件、现行需求、历史交接规则、决策、沟通摘要、实现状态与待办已入包；`SOURCE_PROVENANCE.json` 逐项记录与原机源码的哈希关系 | 逐项阅读规则，按本机合法授权重建账号和业务配置；包不含原始会员资料或浏览器登录状态 |
| 隔离 Python 环境 | 新目录可创建 venv；在未安装依赖的隔离环境中运行测试为 `30 tests, OK (skipped=1)`；浏览器快照入口的 `--help` 可运行 | 安装 `project/requirements.txt` 后重跑测试；跳过项需配置目标 Mac 的音频路径再验 |
| PDF 依赖 | 本次受限执行环境访问 `pypi.org` 时 DNS 失败，因而**未完成独立 venv 的 `pypdf` 安装**；未安装时 `extract_downloaded_pdfs.py` 报 `ModuleNotFoundError: No module named 'pypdf'` | 在能访问依赖源的合法环境中安装 `requirements.txt`，再用获授权的真实 PDF 验证入口；不要把本次测试通过解释为 PDF 入口通过 |
| Mac 音频 | 在本机临时副本填入本机目录后，短文本用 Tingting/Samantha 生成 WAV 与回执成功 | 目标 Mac 须具备对应离线音色，填写 `project/mac_audio_config.json`，以**完整真实报告**生成和核对音频；短文本烟雾测试不能替代整篇验收 |
| 七源与定时交付 | 现存代码可导入、校验真实浏览器证据与交付条件，**尚不能独立控制已登录 Chrome 完成七源采集**；东方财富八股公告接线和完整 Scheduled 运行器也未实现 | 按 `docs/OPEN_WORK.md` 补齐并在目标 MacBook 做一次真实预处理、最终刷新、报告、完整音频、回执及清理的端到端验收 |

因此，本包是**可审计、可继续开发的当前源码交接**。它不是“复制后即可无人值守运行”的完整生产程序；缺少的业务访问、配置、第三方依赖和自动运行入口均在上表及 `docs/OPEN_WORK.md` 明示。原机曾有手动交付，不等于接手设备的真实验收。
