from pathlib import Path

from loguru import logger


def supports(url: str) -> bool:
    return (
        url.startswith("github/")
        or url.startswith("https://github.com/")
        or url.startswith("git@github.com:")
    )


def _get_url_parts(url: str) -> list[str]:
    for prefix in ["github/", "https://github.com/", "git@github.com:"]:
        if url.startswith(prefix):
            url = url.removeprefix(prefix)
            break

    if url.endswith(".git"):
        url = url.removesuffix(".git")

    return url.split("/")


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
    org_name, repo_name = _get_url_parts(url)
    git_addr = f"https://github.com/{org_name}/{repo_name}.git"

    if verbose:
        logger.debug("git address for github is: {}", git_addr)

    return git_addr


def get_local_path(url: str, base_dir: Path) -> Path:
    # 根据规则, 拼装 github 仓库的 git 地址
    org, repo = _get_url_parts(url)

    return base_dir / "github" / org / repo
