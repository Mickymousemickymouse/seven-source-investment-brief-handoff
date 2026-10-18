# 项目重建状态（2026-10-16）

原项目目录被删除；找回的交接压缩包包含需求、配置和 source-reference，但不包含后续迭代的完整程序源码。重建以现行用户要求为准，不能声称找回了原程序。

## 已恢复并核验

- `CURRENT_REQUIREMENTS.md` 与 `SUMMARY_RULES.md` 已合并后续要求，窗口为北京时间前日21:00—当日09:00、当日09:00—21:00。
- `digest/policy.py`、`evidence.py`、`pdf_read.py`、`html_report.py`、`audio.py`、`staging.py` 已恢复报告规则、快照审计、逐页记录、无首行缩进排版、Mac 离线音频及交付检查。
- `browser_bridge.py` 与 `collect_browser_snapshot.py` 可导入真实浏览器列表快照到检查点；列表快照始终标为未完成，不能冒充全文、评论或附件已读。
- `mac_audio_config.json` 将音频明确配置到原机用户的本机 `Music/InvestmentBrief` 目录，`render_report_audio_macos.py` 已用本期报告实跑并核对可播放文件，避免项目 Documents 目录的 iCloud 卸载。外发包不含该原机配置。
- 本地 24 项单元测试通过，仅验证上述代码行为。
- 10月15日21:00晚报已获用户同意手动延时补读：四个星球和三个 X 的网页可见内容、四个星球72小时旧主题网页可见评论、13份可访问PDF共181页、八只持仓证券东方财富公告均有本轮核查记录；一份评论PDF被 Chrome 明确拦截，按用户同意免读并标在报告中。报告及631.73秒离线音频通过文本、文件哈希和音频格式核验，见 `outputs/investment-inbox/reports/2026-10-15-2100-revised-v2-delivery.json`。项目 Documents 音频目录被 macOS 卸载为 `.icloud` 占位文件后，已把可播放成品保存在原机用户的本机 Music 目录并重新核验。这属于手动交付，不是 Scheduled 成功。
- 已核验后只清理下载目录中与本轮PDF清单哈希完全相符的14个文件（13份资料及1份重复副本），约56.2 MB；报告、音频、逐页记录及其他文件保留，见 `evidence/cleanup-20261015-2100.json`。

## 尚未修复或验收

- 代码仍不能自行控制已登录 Chrome 完成七源主题、评论、图片与附件全流程采集；原生主题ID及网页未提供的评论后台总数不能由列表快照证明。用户批准按网页可见评论及本地去重ID验收，须保留限制标注。
- 东方财富八只持仓证券的可重复自动公告接线与正式 Scheduled 端到端成功尚未完成；Windows 并排部署及实机验收也未完成。
- 当前自动任务为 `ACTIVE`，08:00／20:00预整理、09:00／21:00交付。10月15日21:00原 Scheduled 轮超时；手动补报不得记为 Scheduled 成功。
