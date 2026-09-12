# MediaVault 第三方插件示例库

这个仓库是一个**多插件目录**和开发参考。MediaVault 读取根目录的 `catalog.json`，目录中的每个条目都可以单独安装；仓库本身不能直接当作单个插件安装。

```text
https://raw.githubusercontent.com/thsrite/MediaVault-Plugins/main/catalog.json
```

示例插件 `event_audit` 会订阅 v1 事件目录中的全部事件，演示三种入口：

- `plugins/event-audit/mv-plugin.json`：插件 manifest，版本为 `1.0.0`。
- `plugins/event-audit/runner/main.py`：只使用 Python 标准库，通过一次 stdin/stdout JSON 请求完成一次工作。
- `plugins/event-audit/ui/index.html`：自包含插件界面，只通过 `postMessage` 调用已声明的 `preview` action。
- `schedules.hourly_check`：由 MediaVault 保存、启停和调度，插件不创建自己的 cron 或常驻进程。

## 安装示例

1. 在 MediaVault 容器环境变量中配置 `MV_PLUGIN_CATALOG_URL=https://raw.githubusercontent.com/thsrite/MediaVault-Plugins/main/catalog.json`，然后打开 设置中心 → 插件 → 第三方插件。
2. 目录会同时列出未安装和已安装的插件；在「事件审计示例」条目点击安装。
3. 打开配置并保存 JSON；需要接收事件时再启用插件。
4. 在插件配置中启用「每小时检查」即可验证定时任务；点击同一按钮可取消定时。
5. 当目录中的 `version` 高于已安装版本时，条目会显示「更新」，点击后按同一 `source` 和 `subdir` 安装新版本。

GitHub 安装器会固定到某个 commit，并记录仓库、ref、commit 和包 SHA-256。目录条目的 `source` 支持 `github:owner/repo[@ref]`，`subdir` 以仓库根为基准，适合一个仓库发布多个插件。私有目录和私有插件仓库的令牌只从 MediaVault 的 `MV_GITHUB_TOKEN` 环境变量读取，不会写入目录或插件配置。

## 开发文档

完整协议见 [`docs/plugin-development.md`](docs/plugin-development.md)，包括：

- `mv-plugin.json` manifest 和目录约束；
- 全部公开事件、事件 envelope 和失败重试；
- UI iframe bridge 的消息格式与允许动作；
- 定时任务声明、启用、取消和重启恢复；
- bubblewrap 隔离边界与禁止事项；
- 本地测试和发布检查清单。

## 本地检查

示例只依赖 Python 标准库，运行：

```bash
python3 -m unittest discover -s tests -v
```

检查会验证 manifest、事件响应、action 响应和定时任务响应。插件在 MediaVault 中执行时仍必须经过 Linux bubblewrap；本地直接运行只用于协议检查。

## 安全边界

插件代码永远不会被 import 到 MediaVault 进程，也不能导入 `app`、`mediavault` 或访问 MV 的配置、数据库、token、socket、文件系统和任意网络。不要把密钥写进 manifest、UI、事件 payload 或日志。
