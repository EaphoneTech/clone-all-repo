from pathlib import Path
import sys
from git import Repo, InvalidGitRepositoryError, GitCommandError


def update_git(git_repo_url: str, local_dir: Path):
    # 首先尝试已有的 git 目录
    if not local_dir.exists():
        local_dir.mkdir(parents=True, exist_ok=True)

    try:
        repo = Repo(local_dir)

    except InvalidGitRepositoryError:
        # 非 git 目录, 执行 git checkout
        Repo.clone_from(git_repo_url, local_dir)
        return

    try:
        # 已经是 git 目录, 下面要检查一下 remote 是否正确
        origin = repo.remotes["origin"]
    except AttributeError:
        # 已经是 git 目录但是没有 origin, 那么尝试建一个 origin
        origin = repo.create_remote("origin", git_repo_url)

    try:
        origin.pull()
    except GitCommandError as gce:
        print(f"pull {git_repo_url} 时出现错误, {gce}", file=sys.stderr)
