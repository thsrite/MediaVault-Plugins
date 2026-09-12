# MediaVault 第三方源码插件协议 v1

## 1. 运行模型

第三方插件是独立源码包。MediaVault 不加载它的 Python 模块，而是为每次事件、action 或定时任务启动一次隔离进程：

```text
MediaVault ── JSON stdin ──> bubblewrap + /usr/bin/python3 -S ── JSON stdout ──> MediaVault
```

插件代码不得导入 `app`、`mediavault` 或任何 MV Python 对象。双方只交换版本化 JSON。插件不得创建常驻服务、线程、cron、shell、数据库连接或任意 HTTP 客户端。

隔离器清空环境并禁用网络、PID/IPC/user namespace，丢弃全部 capability，只读挂载插件目录为 `/plugin` 和 Python 标准库；声明的固定版本依赖会只读挂载到 `/plugin_deps` 并通过 `PYTHONPATH` 提供。不会挂载 `/app`、MV 配置目录、数据库、home 或 socket。插件进程没有宿主环境变量。没有 Linux bubblewrap 时拒绝执行，不会回退到普通子进程。

## 2. 可安装包格式

单个插件目录必须有唯一的 `mv-plugin.json`。一个 GitHub 仓库可以通过根目录 `catalog.json` 发布多个插件；目录条目的 `subdir` 以仓库根为基准，安装器会定位该子目录。单插件包仍支持 GitHub 自动生成的单层 wrapper 目录。示例目录：

```text
mv-plugin.json
runner/main.py
ui/index.html
```

### 多插件目录

`catalog.json` 是 JSON 数组，每项描述一个可安装插件：

```json
[
  {
    "id": "event_audit",
    "name": "事件审计示例",
    "version": "1.0.0",
    "description": "订阅公开事件",
    "source": "https://github.com/owner/repo/archive/refs/heads/main.zip",
    "subdir": "plugins/event-audit",
    "sha256": "",
    "events": ["media.uploaded"]
  }
]
```

MediaVault 接受压缩包 HTTP(S) 或 `github:owner/repo[@ref]` 形式的 `source`、SemVer `version`、安全的相对 `subdir`、可选 64 位十六进制 `sha256` 和公开事件名。`id` 必须唯一。已安装插件按 `id` 与目录条目配对；目录版本高于本地版本时显示「更新」，更新会下载新版本并原子切换 `current`，旧版本目录保留以便回滚。私有目录 URL 和私有插件仓库共用 `MV_GITHUB_TOKEN`，令牌仅通过请求头发送。

### Manifest

```json
{
  "manifest_version": 1,
  "id": "event_audit",
  "name": "事件审计示例",
  "version": "1.0.0",
  "description": "展示所有公开事件并演示 UI bridge",
  "runtime": "python3-stdlib",
  "entrypoint": "runner/main.py",
  "events": ["media.uploaded"],
  "dependencies": [],
  "permissions": [],
  "config_schema": {
    "type": "object",
    "properties": {"label": {"type": "string", "maxLength": 80}},
    "additionalProperties": false
  },
  "actions": {
    "preview": {
      "title": "预览协议",
      "input_schema": {"type": "object", "additionalProperties": false}
    }
  },
  "schedules": [
    {"id": "hourly_check", "title": "每小时检查", "default_cron": "0 * * * *"}
  ],
  "ui": {"entry": "ui/index.html"}
}
```

约束：

- `id`：小写字母开头，长度 2–64，只能使用小写字母、数字、`_`、`-`。
- `version`：SemVer。每个版本目录不可覆盖，`current` 由 MediaVault 原子切换。
- `runtime`：v1 固定为 `python3-stdlib`；不运行 `setup.py`、`pyproject.toml` 或安装脚本。依赖必须写成固定版本的 PyPI 包（如 `requests==2.32.3`），由用户安装插件时安装并持久化。
- `entrypoint`：只能是包内 `.py` 文件；禁止路径穿越、符号链接、`.so`、`.pyd`、`.pyc` 和重复 zip 条目。
- `events`：只能填写事件目录中的名称；重复项会被去重。
- `permissions`：只能声明 `notifications.send` 或 `media.identify`；每项能力都由宿主校验，不能自行访问 MV 组件。
- `schedules`：最多 16 项，每项包含 `id`、`title` 和可选 `default_cron`。

GitHub 支持 `owner/repo`、`github:owner/repo@ref` 和 `tree` 地址。安装器会先把 ref 解析为 commit SHA，再下载固定 commit；可选 SHA-256 用于阻止包被替换。

## 3. Runner JSON 协议

runner 每次只读取一行 JSON，输出一个 JSON 对象后退出。成功返回：

```json
{"ok": true, "result": {"status": "done"}}
```

失败可返回 `{"ok": false, "error": "可读错误"}` 或使用非零退出码。stdout 上限 1 MiB，单次执行超时 60 秒。事件失败最多重试 8 次，并使用指数退避；插件 stderr 不会作为可信日志返回。

### 配置、存储、通知与日志

插件不能读取环境变量、MV 配置文件、数据库或宿主日志组件。需要配置的字段必须写入 `config_schema`，管理员在 MV 插件页面保存后，runner 会从请求的 `config` 对象读取。需要持久化的小数据使用请求里的 `storage` 快照，并在响应中返回 `storage: {"set": {...}, "delete": [...]}`；宿主会按插件隔离、加密、原子保存。

声明 `notifications.send` 后，响应可返回 `notifications` 数组，由宿主统一发送；插件不接触通知渠道、token 或核心服务。日志同样使用 JSON 响应，不导入任何 MV 模块：

```python
logs = []
def log(level, message, **fields):
    logs.append({"level": level, "message": message, "fields": fields})

log("info", "开始处理", item_count=3)
return {"ok": True, "result": {"processed": 3}, "logs": logs}
```

`level` 支持 `debug`、`info`、`warning`、`error`、`critical`；宿主限制条数和长度，统一添加 `[插件][名称]` 前缀，脱敏后写入 `mediavault.log`。插件页面的“查看日志”使用 `/api/v1/logs/plugin/{plugin_id}`，支持增量刷新、级别/关键词筛选、下载和定时任务运行记录。不要在 `message` 或 `fields` 中放 token、Cookie、密码或完整 URL 凭据。

### 事件请求

```json
{
  "protocol_version": 1,
  "type": "event",
  "event_id": "uuid",
  "event_version": 1,
  "event_type": "media.uploaded",
  "occurred_at": "2026-09-12T08:00:00.000Z",
  "source": "monitor",
  "payload": {"file_name": "movie.mkv"},
  "config": {"label": "archive"}
}
```

`event_id` 可用于插件自己的幂等记录。`payload` 是只读数据，不包含 MV token、Cookie、数据库路径或核心对象。

### Action 请求

UI 或管理端调用 manifest 已声明的 action 时，runner 收到：

```json
{
  "protocol_version": 1,
  "type": "action",
  "request_id": "uuid",
  "action": "preview",
  "payload": {},
  "config": {"label": "archive"}
}
```

action 输入必须符合 manifest 的 `input_schema`，未知字段应拒绝。插件只能实现自己的 action，不能调用 MV 路由或申请隐含权限。

## 4. v1 事件目录

| 事件 | 触发语义 |
| --- | --- |
| `media.uploaded` | 媒体上传最终成功 |
| `media.upload_failed` | 媒体上传最终失败 |
| `media.upload_skipped` | 因重复内容跳过上传 |
| `strm.generated` | STRM 生成完成 |
| `strm.failed` | STRM 生成失败 |
| `library.sync_completed` | 媒体库同步完成 |
| `library.sync_failed` | 媒体库同步失败 |
| `organize.completed` | 整理任务完成 |
| `organize.failed` | 整理任务失败 |
| `subscription.completed` | 订阅任务完成 |
| `subscription.failed` | 订阅任务失败 |
| `download.completed` | 下载任务完成 |
| `download.failed` | 下载任务失败 |
| `backup.completed` | 备份任务完成 |
| `backup.failed` | 备份任务失败 |
| `webhook.received` | 收到媒体服务器 webhook |

事件名、payload 字段和版本只能向后兼容扩展；删除或改变语义需要升级 `event_version`。事件目录中尚未接入业务完成边界的事件不会被伪造触发。

## 5. UI bridge

`ui.entry` 必须是 `ui/` 下不超过 1 MiB 的自包含 HTML。CSS、JavaScript、图片必须内联；禁止远程脚本、字体、网络请求、iframe、form、外部 `src/href/action` 和 `allow-same-origin`。

MediaVault 以 `iframe srcDoc` 加载并设置 CSP，iframe 只有 `sandbox="allow-scripts"`。UI 发送消息：

```js
parent.postMessage({
  channel: 'mv-plugin',
  protocol_version: 1,
  request_id: crypto.randomUUID(),
  action: 'preview',
  payload: {}
}, '*')
```

宿主只接受来自当前 iframe 的消息，限制消息大小和频率，并返回同一个 `request_id`：

```json
{"channel":"mv-plugin","protocol_version":1,"request_id":"uuid","ok":true,"result":{}}
```

v1 内置 bridge 只允许：

- `plugin.get_config`：读取脱敏配置；
- `plugin.save_config`：按 manifest schema 校验并加密保存配置；
- manifest 中声明的插件自有 action。

bridge 不提供任意 HTTP、SQL、shell、核心路由、用户 token、React/Vue 组件或特权对象。

## 6. 定时任务

插件只在 manifest 中声明任务，MediaVault 负责保存、启用、取消和重启恢复：

```json
"schedules": [
  {"id": "hourly_check", "title": "每小时检查", "default_cron": "0 * * * *"}
]
```

启用任务时管理员可以修改 cron；点击「取消定时」会持久化停用状态并停止 host scheduler。每次触发向 runner 发送：

```json
{
  "protocol_version": 1,
  "type": "schedule",
  "task_id": "hourly_check",
  "config": {}
}
```

定时任务与事件共享隔离、60 秒超时和错误记录；同一任务不会并发执行。插件不得自己创建 cron、线程常驻服务或系统任务。

## 7. 发布检查清单

```bash
python3 -m unittest discover -s tests -v
python3 -m json.tool mv-plugin.json >/dev/null
```

发布前还应确认：

1. 单个插件目录内只有一个 `mv-plugin.json`；多插件仓库根目录用 `catalog.json` 列出插件和 `subdir`。
2. 每个目录条目的 `id` 唯一、`version` 为 SemVer，升级版本后检查「更新」按钮。
3. runner 不导入 `app`、`mediavault`，不读取环境变量；第三方依赖必须在 manifest 中固定版本声明。
4. UI 无远程资源、iframe、form 和外部提交地址。
5. 每个事件、action、schedule 都能处理未知字段而不泄露敏感数据。
6. 事件处理具备幂等性，失败时返回明确错误。
7. 仓库不提交 token、Cookie、私钥、生产地址或数据库文件。
