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
  -p, --parallel INTEGER      并行处理的数量  [default: 1]
  --progress / --no-progress  是否显示进度条  [default: progress]
  -v, --verbose               是否打印更详细的日志
  --help                      Show this message and exit.
```

## Configuration

Configuration is done by `repos.yaml`:

```yaml
#repos.yaml

repos:
- repo: github/<github_org_name>/<github_repo_name>
  to: cnb/<cnb_org_name>/<cnb_sub_org_name>/<cnb_repo_name>
- repo: coding/<coding_team_name>/<coding_project_name>/<coding_repo_name>
  to: https://xxx.xxx/xxx.git
```

All `repo` s in the `repos` section will be `git clone`d to local.

Any repo with `to` will be `git push`ed to specified remote.

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

TBD.

```bash
$ docker run -v $(pwd):/app -w /app biggates/clone-all-repo:latest
```
