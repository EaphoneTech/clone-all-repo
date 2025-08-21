from pathlib import Path

from git import GitCommandError, InvalidGitRepositoryError, Repo
from loguru import logger

PUSH_REMOTE_NAME = "push-remote"


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
        Repo.clone_from(git_repo_url, local_dir, mirror=True)
        return

    logger.debug("Pulling latest changes for {}", git_repo_url)

    try:
        origin = repo.remotes.origin
        if origin.url != git_repo_url:
            logger.debug("将 Remote origin URL 设置为 {}", git_repo_url)
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
        origin.fetch()
        logger.info("Successfully fetched latest changes.")
    except GitCommandError as gce:
        logger.error("拉取仓库 {} 时发生错误: {}", git_repo_url, gce)


def push_to_remote(local_git_folder: Path, git_remote_url: str):
    """将已存在的本地 Git 仓库推送到指定的远程仓库。

    Args:
        local_git_folder (Path): 本地 Git 仓库路径
        git_remote_url (str): 要推送的远程仓库地址
    """
    if not local_git_folder.exists():
        print(f"本地仓库路径不存在: {local_git_folder}")
        return

    try:
        repo = Repo(local_git_folder)
    except InvalidGitRepositoryError:
        logger.info(f"指定的路径不是一个 Git 仓库: {local_git_folder}")
        return

    # 添加或更新推送远程仓库
    try:
        push_remote = repo.remotes[PUSH_REMOTE_NAME]
        if push_remote.url != git_remote_url:
            logger.debug("将 {} 的 url 更新为 {}", PUSH_REMOTE_NAME, git_remote_url)
            push_remote.set_url(git_remote_url)
    except IndexError:
        logger.debug("添加远程仓库 {} 为 {}", PUSH_REMOTE_NAME, git_remote_url)
        push_remote = repo.create_remote(PUSH_REMOTE_NAME, git_remote_url)

    # 使用镜像推送
    try:
        logger.debug("{} 开始镜像推送...", local_git_folder.stem)
        push_remote.push(mirror=True)
        logger.debug("{} 镜像推送完成", local_git_folder.stem)
    except Exception as e:
        logger.info(f"{local_git_folder.stem} 镜像推送时发生错误: {e}")

    logger.info(
        "成功将本地仓库 {} 推送到远程: {}", local_git_folder.stem, git_remote_url
    )
