from pathlib import Path

from loguru import logger


def supports(url: str) -> bool:
    return url.startswith("coding/")


def _get_coding_url(team, project, repo_name) -> str:
    return f"https://e.coding.net/{team}/{project}/{repo_name}.git"


def get_url(url: str, verbose: bool = False) -> str:
    """
    根据 coding 的 repo 名字, 返回对应的 git 地址
    :param url: 格式如 coding/<coding_team_name>/<coding_project_name>/<coding_repo_name>
    :param verbose: 是否打印调试信息
    :return: git 地址
    """
    if verbose:
        logger.debug("repo name is: {}", url)

    # 根据规则, 拼装 coding 仓库的 git 地址
    _, team, project, repo_name = url.split("/")
    git_addr = _get_coding_url(team, project, repo_name)

    if verbose:
        logger.debug("git address for coding is: {}", git_addr)

    return git_addr


def get_local_path(url: str, base_dir: Path) -> Path:
    # 根据规则, 拼装 coding 仓库的 git 地址
    _, team, project, repo_name = url.split("/")

    return base_dir / "coding" / team / project / repo_name
