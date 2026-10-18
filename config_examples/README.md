# 配置示例

这里仅给结构与路径范例，不含原设备的私有配置、登录状态或凭据。

- Mac：将 `mac_audio_config.example.json` 复制到 `project/mac_audio_config.json`，把占位用户名改为接手电脑的**实际本机绝对路径**。确认 Tingting、Samantha 均已安装，磁盘可用空间至少 1 GiB，再运行正式音频。不能把示例路径当生产路径。
- Windows：`windows_paths.example.json` 只记录默认 D 盘合同；现有重建包**没有**完整 Windows 运行器、Yaoyao 音频入口或已通过的 Windows 实机部署。旧项目应并排部署，不能用此范例覆盖旧配置。
- 持仓：`holdings.example.json` 是空模板。持仓与关注池由项目所有者按授权在目标设备单独配置，勿把原机的 `holdings.json`、登录文件或会员资料上传到共享代码仓库。
- 四个星球与三个 X 的固定来源身份在当前规则和 `project/digest/policy.py` 中，可供接手者核对；会员登录必须在目标设备实际确认。

原交接包的 `business-paths.json`、`attachment-roots.json`、`audio-paths.json`、`holdings.json`、`watchlist.json` 和 `zsxq-cli-runtime.json` 未作为可上传配置原样打包。后者仅是原设备运行时记录，不能当新设备已获授权或可运行的证据。
