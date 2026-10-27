# clone-all-repo

a python utility that clones multiple git repo, and optionally push to another location.

## Requirements

- python3
- git (must be installed in PATH)

## Arguments

```
Usage: main.py [OPTIONS] [CONFIG_FILE]

  批量 clone 和 push git 仓库

  CONFIG_FILE 默认是 repos.yaml

  -o, --output-dir DIRECTORY  本地 git 仓库的路径  [default: repos]
  -p, --parallel INTEGER      并行处理的数量, 默认取 $CAR_PARALLEL
                              或 repos.yaml 的 defaults.parallel, 否则 1
  --progress / --no-progress  是否显示进度条; 默认取 repos.yaml 的
                              defaults.progress, CI 环境 ($CI) 下自动关闭
  -v, --verbose               是否打印更详细的日志
  --help                      Show this message and exit.
```

退出码: 任一仓库抓取或推送失败时返回 1, 便于流水线感知。

## Configuration

Configuration is done by `repos.yaml`:

```yaml
#repos.yaml

# 全局默认值, 所有仓库继承; 单个仓库用同名键或 refs 覆盖
defaults:
  branches: all           # all | none | [名字或 glob]
  tags: all               # all | none | [名字或 glob]
  pull_refs: none         # none | all | [编号或 glob]
  prune: false            # 是否删除远端残留 ref
  batch_size: 50          # 单次 push 携带的 ref 数
  parallel: 2
  progress: true          # 是否显示进度条, CI 环境下自动关闭

repos:
# 全量镜像: 所有分支 + 所有 tags
- repo: github/<github_org_name>/<github_repo_name>
  to: cnb/<cnb_org_name>/<cnb_sub_org_name>/<cnb_repo_name>

# 重点镜像: 少数分支 + tags 子集
- repo: github/<org>/<repo>
  to: cnb/<org>/<sub>/<repo>
  refs:
    branches: [main, develop, "release/*"]
    tags: ["releases/*"]

- repo: coding/<coding_team_name>/<coding_project_name>/<coding_repo_name>
  to: https://xxx.xxx/xxx.git
```

All `repo` s in the `repos` section will be `git clone`d to local.

Any repo with `to` will be `git push`ed to specified remote.

### ref 选择

| 键 | 取值 | 默认 | 说明 |
| --- | --- | --- | --- |
| `branches` | `all` / `none` / 列表 | `all` | 只影响 `refs/heads/*` |
| `tags` | `all` / `none` / 列表 | `all` | 只影响 `refs/tags/*` |
| `pull_refs` | `none` / `all` / 列表 | `none` | 只影响 `refs/pull/*`, 数量可达数万, 默认关闭 |
| `prune` | 布尔 | `false` | 为真时删除"远端存在 + 命中本次选择 + 本地不存在"的 ref |
| `batch_size` | 整数 | `50` | 单次 push 的 ref 数量, 控制单请求体量 |
| `parallel` | 整数 | `1` | 仓库间并发数, 仅 `defaults` 生效 |
| `progress` | 布尔 | `true` | 是否显示进度条, 仅 `defaults` 生效; `$CI` 为真时自动关闭 |

模式相对命名空间书写, 支持 glob (`*` 可以跨 `/`):

```yaml
refs:
  branches: [main, "release/*"]   # refs/heads/main, refs/heads/release/*
  tags: ["releases/*"]            # refs/tags/releases/*
  pull_refs: [1234]               # refs/pull/1234/*, 也接受 "12*" 这类模式
```

`refs` 内未写的键继承 `defaults`; 列表值整体替换, 不会拼接。

进度条优先级: `--progress` / `--no-progress` > `defaults.progress` >
`$CI` 检测 > 默认开启。CI 平台通常会自动设置 `CI=true`, 因此无需额外配置
就会关闭进度条; 需要强制开启时传 `--progress`。

`branches: all` 不包含 `refs/pull/*`。推送前会先 `ls-remote` 对账, 只推远端
缺失或落后的 ref, 因此失败后重跑会接着上次的进度继续。

## How to use

### Run with cloned repo

1. clone this repo
2. put `repos.yaml` into cloned folder
3. run `python scripts/main.py`

### Run with uv

Put `repos.yaml` into any folder, and run:

```bash
$ uvx --from git+https://github.com/EaphoneTech/clone-all-repo.git clone-all-repo
```

### Install using uv

```bash
$ uv tool install --from git+https://github.com/EaphoneTech/clone-all-repo.git clone-all-repo
```

Once installed, you can run `clone-all-repo` in any folder.

### Upgrade with uv

```bash
$ uv tool upgrade clone-all-repo
```

### Run with docker

```bash
$ docker run -v $(pwd):/app -w /app biggates/clone-all-repo:latest
```

镜像的 entrypoint 是 `clone-all-repo`, 可以追加参数或通过环境变量指定并发数:

```bash
# 命令行参数
$ docker run -v $(pwd):/app -w /app biggates/clone-all-repo:latest -p 4

# 环境变量 (未传 -p 时生效)
$ docker run -e CAR_PARALLEL=4 -v $(pwd):/app -w /app biggates/clone-all-repo:latest
```
