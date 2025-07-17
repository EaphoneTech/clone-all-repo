from pathlib import Path

from loguru import logger


def supports(url: str) -> bool:
    return url.startswith("github/")


def get_url(url: str, verbose: bool = False) -> str:
    """
    根据 github 的 repo 名字, 返回对应的 git 地址
    :param url: 格式如 github/<github_org_name>/<github_repo_name>
    :param verbose: 是否打印调试信息
    :return: git 地址
    """
    if verbose:
        logger.debug("repo name is: {}", url)

    # 根据规则, 拼装 github 仓库的 git 地址
    _, org_name, repo_name = url.split("/")
    git_addr = f"https://github.com/{org_name}/{repo_name}.git"

    if verbose:
        logger.debug("git address for github is: {}", git_addr)

    return git_addr


def get_local_path(url: str, base_dir: Path) -> Path:
    # 根据规则, 拼装 coding 仓库的 git 地址
    _, org, repo = url.split("/")

    return base_dir / "github" / org / repo
