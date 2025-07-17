from pathlib import Path

from git import GitCommandError, InvalidGitRepositoryError, Repo
from loguru import logger


def update_git(git_repo_url: str, local_dir: Path):
    """将 git_repo_url 的 git 仓库 clone 到 local_dir。如果 local_dir 已经有 git 仓库，则执行 pull 操作。

    Args:
        git_repo_url (str): 远程 Git 仓库地址
        local_dir (Path): 本地存储路径
    """
    if not local_dir.exists():
        local_dir.mkdir(parents=True, exist_ok=True)

    try:
        repo = Repo(local_dir)
    except InvalidGitRepositoryError:
        # 非 Git 目录，克隆仓库
        logger.info("Cloning {} to {}", git_repo_url, local_dir)
        Repo.clone_from(git_repo_url, local_dir)
        return

    logger.info("Pulling latest changes for {}", git_repo_url)

    try:
        origin = repo.remotes.origin
        if origin.url != git_repo_url:
            logger.warning("Remote origin URL 不一致，正在更新为: {}", git_repo_url)
            origin.set_url(git_repo_url)
    except AttributeError:
        # 没有 origin，添加 origin 并 fetch
        logger.info("Adding remote origin: {}", git_repo_url)
        origin = repo.create_remote("origin", git_repo_url)
        origin.fetch()

        # 获取默认分支
        try:
            remote_head = origin.refs[0]
            default_branch = remote_head.ref.name.split("/")[-1]
        except IndexError:
            default_branch = "master"
            logger.warning("无法获取远程默认分支，使用默认分支: {}", default_branch)

        # 检出默认分支
        try:
            repo.git.checkout(default_branch)
        except GitCommandError:
            repo.git.checkout("-b", default_branch, f"origin/{default_branch}")

    try:
        # 拉取更新
        origin.pull()
        logger.info("Successfully pulled latest changes.")
    except GitCommandError as gce:
        logger.error("拉取仓库 {} 时发生错误: {}", git_repo_url, gce)


def push_to_remote(local_git_folder: Path, git_remote_url: str):
    """将已存在的本地 Git 仓库推送到指定的远程仓库。

    Args:
        local_git_folder (Path): 本地 Git 仓库路径
        git_remote_url (str): 要推送的远程仓库地址
    """
    if not local_git_folder.exists():
        logger.error("本地仓库路径不存在: {}", local_git_folder)
        return

    try:
        repo = Repo(local_git_folder)
    except InvalidGitRepositoryError:
        logger.error("指定的路径不是一个 Git 仓库: {}", local_git_folder)
        return

    # 确保有远程仓库
    try:
        origin = repo.remotes.origin
        if origin.url != git_remote_url:
            logger.warning("Remote origin URL 不一致，正在更新为: {}", git_remote_url)
            origin.set_url(git_remote_url)
    except AttributeError:
        logger.info("添加远程仓库 origin: {}", git_remote_url)
        origin = repo.create_remote("origin", git_remote_url)

    # 获取所有本地分支
    local_branches = [head.name for head in repo.heads]

    # 获取所有远程分支
    origin.fetch()
    remote_branches = [ref.name for ref in origin.refs]

    # 推送所有本地分支
    for branch in local_branches:
        remote_name = f"refs/heads/{branch}"
        if remote_name in remote_branches:
            logger.info("更新远程分支: {}", branch)
        else:
            logger.info("推送新分支: {}", branch)
        origin.push(refspec=f"refs/heads/{branch}:{remote_name}")

    # 推送所有标签
    tags = [tag.name for tag in repo.tags]
    if tags:
        logger.info("推送标签: {}", ", ".join(tags))
        origin.push("--tags")

    # 可选：推送所有 reflog（用于恢复历史提交）
    # repo.git.push('--all', '--force', '--reflog', 'origin')

    logger.info("成功将本地仓库推送到远程: {}", git_remote_url)
