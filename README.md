# Nodal

Nodal 是一个基于 GitHub Actions 的 Clash 配置自动转换项目。

项目将多个订阅源转换为 Clash/Mihomo 可使用的 YAML 配置，并在转换成功且通过校验后自动提交到当前仓库。

> **重要安全提示**：项目根目录中的无扩展名订阅源文件和生成后的 `*.yaml` 文件都可能包含代理服务器地址、端口以及节点认证信息。公开仓库会公开这些内容。当前工作流优先保持项目原有的简单运行方式，直接读取仓库中的订阅源文件。

## 功能概览

当前工作流位于：

```text
.github/workflows/convert.yml
```

它会执行以下流程：

1. Checkout 当前仓库。
2. 检查根目录中的订阅源文件是否存在且非空。
3. 通过 Runner 本机地址将仓库文件提供给 `subconverter`。
4. 使用固定版本的 `subconverter` 转换为 Clash YAML。
5. 检查生成结果是否有效。
6. 检查代理名称、代理组引用和规则目标。
7. 转换和校验全部成功后，提交并推送对应的 `*.yaml` 文件。
8. 删除 Runner 上的转换程序和日志。

如果任一订阅缺失、转换失败或校验失败，工作流会停止，并且不会用错误内容覆盖已有 YAML 文件。

## 项目结构

```text
.
├── .github/
│   └── workflows/
│       └── convert.yml       # GitHub Actions 自动转换工作流
├── FYH002                  # Base64 编码的订阅源示例
├── HMQ006                  # Base64 编码的订阅源示例
├── HYL001                  # Base64 编码的订阅源示例
├── LXS004                  # Base64 编码的订阅源示例
├── WXQ005                  # Base64 编码的订阅源示例
├── WXY003                  # Base64 编码的订阅源示例
├── vpn                     # Base64 编码的订阅源示例
├── FYH002.yaml             # 生成的 Clash 配置
├── HMQ006.yaml
├── HYL001.yaml
├── LXS004.yaml
├── WXQ005.yaml
├── WXY003.yaml
├── vpn.yaml
└── README.md
```

工作流直接读取根目录下的无扩展名订阅源文件。文件内容通常是 Base64 编码的节点订阅，工作流不会在日志中打印其内容。

## 配置订阅源文件

在仓库根目录保留以下 7 个文件：

```text
HMQ006
HYL001
LXS004
FYH002
WXQ005
WXY003
vpn
```

文件名必须完全匹配，其中 VPN 源文件名称为小写 `vpn`。如果使用自己的订阅源，请确保文件内容是 `subconverter` 支持的格式，并保持 Base64 编码完整。

### 不要提交未经授权的凭据

如果仓库历史或公开文件曾经包含真实节点密码、UUID 或订阅链接，应先完成以下操作：

1. 在节点服务商处吊销旧密码和 UUID。
2. 生成全新的节点凭据。
3. 生成新的订阅源。
4. 更新仓库中的源文件。
5. 清理 Git 历史中的旧凭据，避免旧提交继续暴露。

Base64 只是编码，不是加密。任何拿到 Base64 内容的人都可以将其解码。

## 触发工作流

工作流支持三种触发方式。

### 手动运行

进入：

```text
Actions → Convert subscriptions to Clash → Run workflow
```

### 定时运行

默认每 6 小时运行一次：

```yaml
schedule:
  - cron: '0 */6 * * *'
```

GitHub Actions 使用 UTC 时间。该表达式表示 UTC 时间每天的 00:00、06:00、12:00 和 18:00 运行。

### 修改工作流时自动运行

当 `.github/workflows/convert.yml` 发生提交时会触发一次工作流。

生成的 YAML 提交不会再次触发本工作流，因为工作流忽略根目录下的 `*.yaml` 文件：

```yaml
push:
  paths-ignore:
    - '*.yaml'
```

## 生成的配置

每个订阅源文件对应一个生成的 YAML 文件：

| 订阅源文件 | 输出文件 |
|---|---|
| `HMQ006` | `HMQ006.yaml` |
| `HYL001` | `HYL001.yaml` |
| `LXS004` | `LXS004.yaml` |
| `FYH002` | `FYH002.yaml` |
| `WXQ005` | `WXQ005.yaml` |
| `WXY003` | `WXY003.yaml` |
| `vpn` | `vpn.yaml` |

当前转换参数包括：

- 目标格式：Clash
- UDP：开启
- TCP Fast Open：开启
- 插入额外配置：关闭
- 证书校验：开启
- ACL4SSR 在线配置：用于生成分流规则
- `subconverter`：固定使用 `v0.9.0`

## 转换校验规则

工作流不会直接覆盖已有配置，而是先写入临时文件。临时文件必须满足以下条件才会替换正式 YAML：

- 文件非空。
- 不包含 `No nodes were found` 等错误信息。
- 包含 `proxies`。
- 包含 `proxy-groups`。
- 包含 `rules`。
- YAML 根节点是对象。
- `proxies`、`proxy-groups` 和 `rules` 都是非空列表。
- 代理名称不能重复。
- 代理组引用必须存在。
- 分流规则目标必须存在。

因此，当某个上游订阅暂时失效时，工作流会失败并保留上一次有效的 YAML，而不会把错误文本提交进仓库。

## 工作流权限

工作流需要将生成的 YAML 推送回当前仓库，因此使用：

```yaml
permissions:
  contents: write
```

如果 Actions 运行时提示没有推送权限，请检查：

```text
Settings → Actions → General → Workflow permissions
```

确认允许 GitHub Actions 读写仓库内容。

## 本地检查

查看工作流状态：

```bash
git status --short --branch
```

检查 YAML 语法：

```bash
python3 -m pip install PyYAML
python3 - <<'PY'
from pathlib import Path
import yaml

for path in sorted(Path('.').glob('*.yaml')):
    try:
        data = yaml.safe_load(path.read_text(encoding='utf-8'))
        print(f'{path}: root={type(data).__name__}')
    except Exception as exc:
        print(f'{path}: ERROR: {exc}')
PY
```

检查订阅源是否可以被 Base64 解码：

```bash
base64 --decode FYH002 | head
```

不要将解码后的输出粘贴到 Issue、Pull Request、日志或聊天中。

## 常见故障

### `Missing or empty repository source file`

说明工作流没有找到对应的仓库源文件。检查文件是否位于仓库根目录、名称是否完全匹配，以及文件是否为空。

### `No nodes were found!`

说明 `subconverter` 没有从对应订阅源解析到节点。常见原因：

- 源文件不是完整 Base64 内容。
- 源文件已经被重复 Base64 编码。
- 订阅源已失效。
- 节点服务商返回了错误页面。
- 节点格式不再被当前版本的 `subconverter` 支持。

### YAML 校验失败

查看 Actions 运行日志，重点检查：

- `proxies` 是否为空。
- `proxy-groups` 是否引用了不存在的节点。
- `rules` 的最后一个字段是否引用了不存在的代理组。

### `git push` 失败

检查：

- 工作流是否包含 `permissions: contents: write`。
- 仓库 Actions 是否允许写入。
- 分支保护规则是否禁止 GitHub Actions 直接推送。
- 是否有其他并发工作流正在更新同一分支。

## 安全边界与改进建议

当前方案的安全边界是：

- 工作流直接读取公开仓库中的订阅源文件。
- 源文件和生成后的 YAML 都可能包含节点信息，因此公开仓库会公开这些内容。
- 转换时通过 Runner 本机地址提供源文件，不依赖外部 Raw URL 拉取。
- 工作流完成后会删除 Runner 上的转换程序和日志。

如果需要真正隐藏节点凭据，不应将生成的 YAML 提交到公开仓库。可以改用：

- 私有 GitHub 仓库保存生成配置。
- 私有对象存储。
- 需要认证的订阅分发服务。
- 运行时动态生成并通过鉴权接口返回配置。

## 许可证与使用责任

本仓库主要保存订阅转换配置和自动化脚本。请确保你拥有所使用节点、订阅内容、规则集和第三方服务的合法使用权。

请不要将他人的节点凭据、个人订阅链接或未授权的服务配置提交到仓库。
