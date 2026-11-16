# Nodal

Nodal 是一个基于 GitHub Actions 和 GitHub Pages 的 Clash/Mihomo 订阅转换项目。

项目会读取仓库根目录中的订阅源文件，将其中的代理节点转换为 Clash/Mihomo YAML 配置，执行结构校验和 Mihomo 内核级校验，校验通过后自动提交并发布到 GitHub Pages。

> **重要安全提示**：仓库中的无扩展名订阅源文件和生成的 `.yaml` 文件可能包含服务器地址、端口、UUID、密码、Reality 公钥、Short ID 等节点认证信息。Base64 只是编码，不是加密。公开仓库会公开这些内容，请确认你拥有相关订阅和节点的合法使用权。

## 目录

- [功能概览](#功能概览)
- [线上订阅地址](#线上订阅地址)
- [项目结构](#项目结构)
- [支持的订阅源格式](#支持的订阅源格式)
- [新增订阅源](#新增订阅源)
- [更新订阅节点](#更新订阅节点)
- [删除订阅源](#删除订阅源)
- [自动转换流程](#自动转换流程)
- [策略组说明](#策略组说明)
- [测速设置](#测速设置)
- [现代协议兼容](#现代协议兼容)
- [GitHub Actions](#github-actions)
- [本地测试](#本地测试)
- [常见问题](#常见问题)
- [安全注意事项](#安全注意事项)
- [维护说明](#维护说明)

## 功能概览

Nodal 当前提供以下能力：

- 自动发现仓库根目录下符合规则的订阅源文件；
- 支持标准 Base64、Base64URL 和省略末尾 `=` padding 的 Base64 内容；
- 使用固定版本的 `subconverter` 进行传统 Clash 配置转换；
- 使用自定义脚本补回 `VLESS` 和 `Hysteria2` 等现代节点；
- 自动生成协议策略组、地区策略组和故障切换组；
- 自动删除不存在协议对应的空策略组；
- 统一策略组排序，方便在 Clash Mi 等客户端中使用；
- 检查节点名称、策略组引用和规则目标；
- 使用固定版本 Mihomo 执行真实的配置级 `-t` 校验；
- 转换失败时使用固定的通用 Mihomo 回退模板；
- 所有源转换和校验成功后才提交生成 YAML；
- 通过 GitHub Pages 提供线上订阅地址；
- 每 6 小时自动重新处理仓库中的现有订阅源。

## 线上订阅地址

GitHub Pages 地址为：

```text
https://jettking.github.io/Nodal/
```

每个源文件对应一个同名 YAML 文件。当前示例地址如下：

```text
https://jettking.github.io/Nodal/vpn.yaml
https://jettking.github.io/Nodal/FYH002.yaml
https://jettking.github.io/Nodal/HMQ006.yaml
https://jettking.github.io/Nodal/HYL001.yaml
https://jettking.github.io/Nodal/LXS004.yaml
https://jettking.github.io/Nodal/WXQ005.yaml
https://jettking.github.io/Nodal/WXY003.yaml
https://jettking.github.io/Nodal/XPH007.yaml
```

在 Clash Mi、Clash Meta、Mihomo Party 或其他兼容客户端中，添加对应的 YAML URL 即可。

> GitHub Actions 完成后，GitHub Pages 还需要短暂的部署时间。若刚更新后客户端仍读取旧内容，请等待 Pages 发布完成后再更新订阅。

## 项目结构

```text
.
├── .github/
│   └── workflows/
│       └── convert.yml          # 转换、校验、提交和发布工作流
├── scripts/
│   ├── discover_sources.py      # 自动发现和解码订阅源
│   ├── merge_mihomo_nodes.py    # 合并 VLESS/Hysteria2 并生成策略组
│   └── prune_generated_configs.py # 清理已删除源对应的 YAML
├── templates/
│   └── mihomo-base.yaml         # 固定的通用 Mihomo 回退模板
├── tests/
│   └── test_merge_mihomo_nodes.py # 单元测试
├── vpn                          # Base64 订阅源
├── FYH002                       # Base64 订阅源
├── HMQ006                       # Base64 订阅源
├── HYL001                       # Base64 订阅源
├── LXS004                       # Base64 订阅源
├── WXQ005                       # Base64 订阅源
├── WXY003                       # Base64 订阅源
├── XPH007                       # Base64 订阅源
├── vpn.yaml                     # 自动生成的 Clash/Mihomo 配置
├── FYH002.yaml                  # 自动生成的 Clash/Mihomo 配置
├── HMQ006.yaml
├── HYL001.yaml
├── LXS004.yaml
├── WXQ005.yaml
├── WXY003.yaml
├── XPH007.yaml
└── README.md
```

仓库中的 `.yaml` 文件是生成文件，不建议手动编辑。需要调整节点时，应修改对应的无扩展名源文件。

## 支持的订阅源格式

源文件必须位于仓库根目录，并满足以下条件：

- 文件没有扩展名；
- 文件名只包含英文字母、数字、下划线或短横线；
- 文件不是隐藏文件、目录或脚本文件；
- 文件内容是标准 Base64 或 Base64URL 编码的 UTF-8 文本；
- Base64 末尾可以省略 `=` padding；
- 解码后的内容至少包含一个受支持的代理 URI。

当前自动发现逻辑识别以下协议前缀：

```text
vmess://
vless://
trojan://
ss://
ssr://
hysteria://
hysteria2://
hy2://
tuic://
anytls://
socks://
socks5://
http://
wireguard://
wg://
```

其中，`subconverter` 负责传统协议的转换；项目自定义脚本重点补回并规范化 `VLESS` 和 `Hysteria2` 节点。

## 新增订阅源

假设要新增一个名为 `NEW001` 的源文件。

### 1. 准备源内容

源文件内容应是节点 URI 列表的 Base64 或 Base64URL 编码，例如原始内容可能是：

```text
vless://...
hysteria2://...
```

不要把解码后的真实节点内容提交到 Issue、Pull Request 或日志中。

### 2. 创建根目录文件

```bash
cp /path/to/encoded-subscription ./NEW001
```

文件名不能写成：

```text
NEW001.txt
NEW001.yaml
```

### 3. 本地检查

```bash
python3 scripts/discover_sources.py
```

如果源文件有效，输出中应包含：

```text
NEW001
```

也可以单独测试解码：

```bash
python3 -c 'from pathlib import Path; from scripts.discover_sources import decode_source; print(len(decode_source(Path("NEW001")).splitlines()))'
```

### 4. 提交并推送

```bash
git add NEW001
git commit -m "feat: add NEW001 subscription"
git push origin main
```

推送后，GitHub Actions 会自动发现 `NEW001`，并生成：

```text
NEW001.yaml
```

线上地址为：

```text
https://jettking.github.io/Nodal/NEW001.yaml
```

不需要手动修改 `convert.yml` 中的源列表。

## 更新订阅节点

如果要更新某个源中的节点，只需要替换对应的无扩展名源文件。

例如更新 `NEW001`：

```bash
# 用新的 Base64/Base64URL 内容替换 NEW001
vim NEW001

git add NEW001
git commit -m "chore: update NEW001 nodes"
git push origin main
```

GitHub Actions 会执行：

```text
读取 NEW001
  ↓
解码和检查源内容
  ↓
subconverter 转换
  ↓
补回 VLESS/Hysteria2 节点
  ↓
生成并排序策略组
  ↓
PyYAML 结构检查
  ↓
Mihomo 内核 -t 检查
  ↓
提交 NEW001.yaml
  ↓
GitHub Pages 发布
```

如果转换或校验失败，工作流会停止，并保留上一次有效的 `NEW001.yaml`，不会用错误内容覆盖线上配置。

> 定时任务只会重新处理仓库中已有的源文件。它不会自动访问服务商 URL 下载最新源内容，除非你手动更新源文件或另外实现外部订阅拉取逻辑。

## 删除订阅源

删除根目录中的源文件即可：

```bash
git rm NEW001
git commit -m "chore: remove NEW001 subscription"
git push origin main
```

下一次工作流会在所有剩余源都成功转换和校验后删除：

```text
NEW001.yaml
```

如果其他源转换失败，清理步骤不会执行，旧的 YAML 会被保留。

## 自动转换流程

工作流文件位于：

```text
.github/workflows/convert.yml
```

完整流程如下：

1. Checkout 仓库；
2. 自动发现合法源文件；
3. 检查 Base64/Base64URL、UTF-8 和代理 URI；
4. 下载固定版本并校验 SHA-256 的 `subconverter`；
5. 在 Runner 本机启动源文件 HTTP 服务和 subconverter；
6. 为每个源生成临时 YAML；
7. 如果 subconverter 无法处理现代节点，则使用固定回退模板；
8. 使用 `merge_mihomo_nodes.py` 补回 VLESS/Hysteria2；
9. 删除空的协议策略组；
10. 按统一顺序重排策略组；
11. 使用 PyYAML 检查配置结构和引用；
12. 使用固定 Mihomo 内核执行配置级测试；
13. 删除已不存在源对应的旧 YAML；
14. 只有全部验证通过后才提交生成文件；
15. GitHub Pages 自动发布生成结果。

### 固定工具版本

当前工作流固定使用：

```text
subconverter: v0.9.0
Mihomo:       v1.19.34
```

工具下载包会通过 SHA-256 校验，避免下载内容被意外替换。

## 策略组说明

策略组会根据配置中实际存在的节点动态生成。没有对应协议节点时，不会生成空策略组。

### 固定排序

策略组按以下顺序排列：

```text
🚀 节点选择
♻️ 自动选择
🔁 故障切换
⚡ Hysteria2 自动
🔐 VLESS 自动
🚀 Trojan 自动
🇭🇰 香港自动
🇯🇵 日本自动
🇸🇬 新加坡自动
🇺🇸 美国自动
🌐 其他地区自动
🌍 国外媒体
📲 电报信息
Ⓜ️ 微软服务
🍎 苹果服务
📢 谷歌FCM
🎯 全球直连
🛑 全球拦截
🍃 应用净化
🐟 漏网之鱼
```

实际不存在的协议组或地区组会跳过。例如只有 VLESS 的订阅不会生成：

```text
⚡ Hysteria2 自动
🚀 Trojan 自动
```

自定义的、未被固定排序表识别的策略组会保留在末尾。

### 空策略组保护

以下类型的策略组必须至少有 `proxies` 或 `use`：

```text
select
url-test
fallback
load-balance
```

如果工作流发现空组、无效节点引用或无效规则目标，会直接失败并阻止发布。

## 测速设置

当前所有线上配置统一使用：

```yaml
url: https://www.gstatic.com/generate_204
interval: 300
```

含义是每 300 秒进行一次测速或可用性检查。

当前容差设置为：

```text
♻️ 自动选择：tolerance=50
协议自动组和地区自动组：tolerance=80
```

`🔁 故障切换` 是 `fallback` 组，不使用 `tolerance`，只根据节点可用性进行切换。

当前没有显式设置 `timeout`，因此节点测速超时使用 Mihomo 内核默认值。工作流中的：

```text
--connect-timeout 15
--max-time 180
```

是 GitHub Actions 调用 subconverter 的 HTTP 超时，不是 Clash/Mihomo 节点测速超时。

## 现代协议兼容

### VLESS

项目会尝试保留和转换常见 VLESS 字段，包括：

- UUID；
- TLS；
- SNI/ServerName；
- XTLS Vision 流控；
- Reality 公钥和 Short ID；
- 客户端指纹；
- WebSocket；
- gRPC；
- HTTP/H2 传输；
- TCP Fast Open。

### Hysteria2

项目会尝试保留和转换常见 Hysteria2 字段，包括：

- 密码；
- SNI；
- 跳过证书校验；
- 端口跳跃范围；
- 混淆类型；
- 混淆密码；
- ALPN。

YAML 格式正确并不代表节点服务端一定有效。UUID、密码、Reality 公钥、Short ID 或服务端配置失效时，仍需要更换节点源。

## GitHub Actions

### 触发方式

工作流支持以下触发方式：

- 推送源文件、脚本、模板或工作流修改；
- 手动运行；
- 每 6 小时运行一次的定时任务。

定时表达式为：

```yaml
schedule:
  - cron: '0 */6 * * *'
```

GitHub Actions 使用 UTC 时间，对应每天 UTC 的 00:00、06:00、12:00 和 18:00。

生成的 `.yaml` 文件不会再次触发同一个转换工作流，以避免提交循环。

### 查看运行结果

进入 GitHub 仓库的：

```text
Actions → Convert subscriptions to Clash
```

重点查看以下步骤：

```text
Validate repository source files
Download pinned subconverter
Download pinned Mihomo
Convert subscriptions from repository files
Validate generated YAML and references
Commit and push validated YAML
```

如果转换成功但线上暂时没有更新，还需要等待：

```text
pages-build-deployment
```

完成后再在客户端更新订阅。

### 工作流权限

工作流需要提交自动生成的 YAML，因此使用：

```yaml
permissions:
  contents: write
```

如果出现 `git push` 权限错误，请在仓库设置中确认：

```text
Settings → Actions → General → Workflow permissions
```

并允许 GitHub Actions 读写仓库内容。

## 本地测试

### 运行单元测试

```bash
python3 -m unittest discover -s tests -v
```

### 检查 Python 语法

```bash
python3 -m py_compile scripts/*.py tests/*.py
```

### 检查工作流和 YAML 语法

```bash
python3 - <<'PY'
from pathlib import Path
import yaml

for path in [Path('.github/workflows/convert.yml'), *sorted(Path('.').glob('*.yaml'))]:
    yaml.safe_load(path.read_text(encoding='utf-8'))
    print(f'{path}: OK')
PY
```

### 检查源文件发现

```bash
python3 scripts/discover_sources.py
```

### 检查工作区

```bash
git status --short --branch
git diff --check
```

## 常见问题

### Clash Mi 报 `startVPNTunnel status timeout`

先查看后续的具体错误。若同时出现：

```text
'use' or 'proxies' missing
```

通常是配置中存在空策略组。当前工作流已经自动删除空协议组，并在发布前阻止空组配置。

建议删除 Clash Mi 中的旧配置后重新导入最新 YAML。

### 配置能导入但没有网络

按以下顺序检查：

1. 是否选择了正确的主策略组；
2. 主策略组是否实际引用了有节点的协议组；
3. 是否误选了空或不存在的协议组；
4. 节点服务端是否仍然有效；
5. Clash Mi 当前是否已经启动 iOS VPN Tunnel；
6. 当前 Wi-Fi 或蜂窝网络是否阻断了对应协议。

如果日志出现 `REALITY handshake failed`、`invalid public key` 或 `invalid short id`，通常是服务端 Reality 参数失效，而不是 YAML 排序问题。

### 新增文件没有生成 YAML

检查：

- 文件是否位于仓库根目录；
- 文件是否带有扩展名；
- 文件名是否包含空格或其他特殊字符；
- 内容是否能被 Base64/Base64URL 解码；
- 解码后是否包含受支持的代理 URI；
- 是否已经提交并推送到远程 `main` 分支。

### 工作流失败后旧 YAML 是否会消失

正常不会。工作流会在所有源文件转换和校验成功后才执行旧 YAML 清理。任意源转换失败时，清理步骤不会执行，已有生成文件会被保留。

### 修改 YAML 后为什么没有触发工作流

`.yaml` 文件是生成文件，工作流会忽略根目录 YAML 的推送事件。请修改对应的无扩展名源文件，不要直接编辑生成 YAML。

### 为什么线上仍是旧内容

可能是以下原因：

- 转换工作流还没有完成；
- 自动生成提交还没有产生；
- GitHub Pages 还没有部署完成；
- 客户端缓存了旧订阅；
- 客户端更新的是另一个 YAML 地址。

请依次检查 `Convert subscriptions to Clash` 和 `pages-build-deployment` 两个工作流。

## 安全注意事项

### Base64 不是加密

任何拿到源文件的人都可以解码节点内容。因此不要把 Base64 当作凭据保护方案。

### 公开仓库会暴露节点信息

公开仓库中的源文件和 YAML 可能包含：

- 节点域名或 IP；
- 端口；
- UUID；
- 密码；
- Reality 公钥和 Short ID；
- 其他协议认证信息。

如果这些信息属于真实、私有或未授权的订阅，不应直接提交到公开仓库。

### 凭据泄露后的处理

如果真实节点凭据曾经被公开：

1. 在服务商处吊销旧 UUID、密码或订阅；
2. 生成新的节点凭据；
3. 更新源文件；
4. 必要时清理 Git 历史；
5. 确认旧提交和缓存不会继续提供敏感内容。

清理 Git 历史属于有影响的操作，执行前应确认仓库协作者和部署方式。

### 更安全的部署方式

如果需要隐藏节点凭据，可以考虑：

- 使用私有 GitHub 仓库；
- 将订阅 URL 保存到 GitHub Secrets；
- 在 Actions 中临时下载源内容；
- 使用需要鉴权的对象存储或订阅分发服务；
- 不把原始源文件和最终 YAML 长期提交到公开仓库。

## 维护说明

### 修改转换逻辑

主要代码位于：

```text
scripts/discover_sources.py
scripts/merge_mihomo_nodes.py
scripts/prune_generated_configs.py
```

修改后至少运行：

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile scripts/*.py tests/*.py
git diff --check
```

### 修改策略组排序

策略组固定顺序由 `scripts/merge_mihomo_nodes.py` 中的排序表控制。新增策略组时，应同时考虑：

- 是否需要加入固定排序；
- 没有对应节点时是否应该省略；
- 是否需要加入主节点选择组；
- 是否会造成空组或无效引用；
- 是否需要增加单元测试。

### 修改 Mihomo 版本

更新 Mihomo 版本时必须同时修改：

```text
MIHOMO_VERSION
MIHOMO_ASSET
MIHOMO_SHA256
```

修改后应先在本地下载对应构建并验证 SHA-256，再运行现有 YAML 的 Mihomo 配置测试，最后提交并观察 GitHub Actions 结果。

### 修改回退模板

固定回退模板位于：

```text
templates/mihomo-base.yaml
```

模板必须满足：

- 根节点是 YAML mapping；
- 包含 `proxies`、`proxy-groups` 和 `rules`；
- 不能存在空的 `select`、`url-test`、`fallback` 或 `load-balance` 组；
- 策略组引用必须有效；
- 能通过 Mihomo `-t` 校验。

## 许可证与使用责任

本项目主要保存订阅转换脚本、规则配置和自动化流程。请确认你拥有所使用节点、订阅内容、规则集和第三方服务的合法使用权。

请不要将他人的节点凭据、个人订阅链接或未授权的服务配置提交到仓库。
