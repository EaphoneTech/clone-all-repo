from pathlib import Path

from loguru import logger


def supports(url: str) -> bool:
    return (
        url.startswith("coding/")
        or url.startswith("https://e.coding.net/")
        or url.startswith("git@e.coding.net:")
    )


def _get_url_parts(url: str) -> list[str]:
    for prefix in ["coding/", "https://e.coding.net/", "git@e.coding.net:"]:
        if url.startswith(prefix):
            url = url.removeprefix(prefix)
            break

    if url.endswith(".git"):
        url = url.removesuffix(".git")

    parts = url.split("/")
    if len(parts) == 2:
        parts.append(parts[-1])

    return parts


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
    team, project, repo_name = _get_url_parts(url)
    git_addr = f"https://e.coding.net/{team}/{project}/{repo_name}.git"

    if verbose:
        logger.debug("git address for coding is: {}", git_addr)

    return git_addr


def get_local_path(url: str, base_dir: Path) -> Path:
    # 根据规则, 拼装 coding 仓库的 git 地址
    team, project, repo_name = _get_url_parts(url)

    return base_dir / "coding" / team / project / repo_name
