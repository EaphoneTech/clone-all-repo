from pathlib import Path

from git import GitCommandError, InvalidGitRepositoryError, Repo
from loguru import logger


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

        # 有的时候 origin 没有 master 分支, 要怎么处理?
        origin.fetch()

        try:
            # 尝试获取远程的 HEAD 引用
            remote_head = origin.refs[0]
            default_branch = remote_head.ref.name.split("/")[-1]
            # 切换到默认分支
            repo.git.checkout(default_branch)
        except Exception:
            repo.git.checkout("master")

    try:
        origin.pull()
    except GitCommandError as gce:
        logger.error("pull {} 时出现错误, {}", git_repo_url, gce)
