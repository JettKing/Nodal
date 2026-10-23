# Nodal

Nodal 是一个基于 GitHub Actions 的 Clash 配置自动转换项目。

项目将多个订阅源转换为 Clash/Mihomo 可使用的 YAML 配置，并在转换成功且通过校验后自动提交到当前仓库。

> **重要安全提示**：生成后的 `*.yaml` 文件包含代理服务器地址、端口以及节点认证信息。只要这些文件被提交到公开仓库，节点信息就会公开。本项目当前采用“输入订阅源使用 GitHub Secrets，生成配置继续提交到公开仓库”的方案，因此它只能保护原始订阅源，不能隐藏生成后的节点配置。

## 功能概览

当前工作流位于：

```text
.github/workflows/convert.yml
```

它会执行以下流程：

1. 从 GitHub Actions Secrets 读取订阅源。
2. 将订阅源临时写入 GitHub Runner 的临时目录。
3. 仅通过本机地址提供给 `subconverter`，不从公开 Raw URL 读取原始订阅。
4. 使用固定版本的 `subconverter` 转换为 Clash YAML。
5. 检查生成结果是否有效。
6. 检查代理名称、代理组引用和规则目标。
7. 转换和校验全部成功后，提交并推送对应的 `*.yaml` 文件。
8. 删除 Runner 上的临时订阅文件和转换日志。

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

工作流当前不读取根目录下的无扩展名订阅源文件；这些文件仅作为格式参考或本地备用文件。自动转换使用 GitHub Secrets 中的内容。

## 配置 GitHub Secrets

进入 GitHub 仓库：

```text
Settings → Secrets and variables → Actions → New repository secret
```

创建以下 7 个 Repository secrets：

```text
NODAL_HMQ006
NODAL_HYL001
NODAL_LXS004
NODAL_FYH002
NODAL_WXQ005
NODAL_WXY003
NODAL_VPN
```

Secret 名称必须完全匹配。`vpn` 对应的 Secret 名称是大写的 `NODAL_VPN`。

### Secret 的值是什么

每个 Secret 的值应当是对应订阅源文件的完整 Base64 内容，而不是直接粘贴解码后的多行节点链接。

例如，本地文件为：

```text
FYH002
```

则可以使用 GitHub CLI 写入：

```bash
gh secret set NODAL_FYH002 < FYH002
gh secret set NODAL_HMQ006 < HMQ006
gh secret set NODAL_HYL001 < HYL001
gh secret set NODAL_LXS004 < LXS004
gh secret set NODAL_WXQ005 < WXQ005
gh secret set NODAL_WXY003 < WXY003
gh secret set NODAL_VPN < vpn
```

也可以在 GitHub 网页中手动粘贴 Base64 内容。

### 不要直接复用已经泄露的凭据

如果仓库历史或公开文件曾经包含真实节点密码、UUID 或订阅链接，应先完成以下操作：

1. 在节点服务商处吊销旧密码和 UUID。
2. 生成全新的节点凭据。
3. 生成新的订阅源。
4. 将新订阅源写入 Secrets。
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

生成的 YAML 提交不会再次触发本工作流，因为工作流只监听工作流文件本身：

```yaml
push:
  paths:
    - '.github/workflows/convert.yml'
```

## 生成的配置

每个 Secret 对应一个生成的 YAML 文件：

| Secret | 输出文件 |
|---|---|
| `NODAL_HMQ006` | `HMQ006.yaml` |
| `NODAL_HYL001` | `HYL001.yaml` |
| `NODAL_LXS004` | `LXS004.yaml` |
| `NODAL_FYH002` | `FYH002.yaml` |
| `NODAL_WXQ005` | `WXQ005.yaml` |
| `NODAL_WXY003` | `WXY003.yaml` |
| `NODAL_VPN` | `vpn.yaml` |

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

### `Missing required GitHub Secret`

说明工作流没有找到对应的 Secret。检查：

- Secret 是否创建在正确的仓库中。
- 名称是否完全匹配。
- `vpn` 是否使用 `NODAL_VPN`。
- Secret 是否为空。

### `No nodes were found!`

说明 `subconverter` 没有从对应订阅源解析到节点。常见原因：

- Secret 内容不是完整 Base64 内容。
- Secret 内容已经被重复 Base64 编码。
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

- 原始订阅源从 GitHub Secrets 读取，不再依赖公开 Raw 文件。
- Secret 内容只在 Runner 临时目录中使用。
- 工作流完成后会删除临时订阅文件和日志。
- 生成后的 YAML 会提交到公开仓库，因此其中的节点信息仍然公开。

如果需要真正隐藏节点凭据，不应将生成的 YAML 提交到公开仓库。可以改用：

- 私有 GitHub 仓库保存生成配置。
- 私有对象存储。
- 需要认证的订阅分发服务。
- 运行时动态生成并通过鉴权接口返回配置。

## 许可证与使用责任

本仓库主要保存订阅转换配置和自动化脚本。请确保你拥有所使用节点、订阅内容、规则集和第三方服务的合法使用权。

请不要将他人的节点凭据、个人订阅链接或未授权的服务配置提交到仓库。