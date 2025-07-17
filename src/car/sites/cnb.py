from pathlib import Path

from loguru import logger


def supports(url: str) -> bool:
    return url.startswith("cnb/")


def get_url(url: str, verbose: bool = False) -> str:
    """
    根据 cnb 的 repo 名字, 返回对应的 git 地址
    :param url: 格式如 cnb/<cnb_org_name>/<cnb_sub_org_name>/<cnb_repo_name>
    :param verbose: 是否打印调试信息
    :return: git 地址
    """
    if verbose:
        logger.debug("repo name is: {}", url)

    # 根据规则, 拼装 cnb 仓库的 git 地址
    _, org_name, sub_org_name, repo_name = url.split("/")
    git_addr = f"https://cnb.cool/{org_name}/{sub_org_name}/{repo_name}.git"

    if verbose:
        logger.debug("git address for cnb is: {}", git_addr)

    return git_addr


def get_local_path(url: str, base_dir: Path) -> Path:
    # 根据规则, 拼装 coding 仓库的 git 地址
    _, org_name, sub_org_name, repo_name = url.split("/")

    return base_dir / "cnb" / org_name / sub_org_name / repo_name
