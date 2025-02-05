from pathlib import Path

from loguru import logger

from ..git_ops import update_git


def process(site: dict, dest_folder: Path, verbose: bool = False):
    team = site["team"]
    projects = site["projects"]
    for project in projects:
        repos = project["repos"]
        project_name = project["project"]
        for repo_name in repos:
            # 根据规则, 拼装 coding 仓库的 git 地址
            git_addr = f"https://e.coding.net/{team}/{project_name}/{repo_name}.git"

            local_git_folder_name = f"coding/{team}/{project_name}/{repo_name}"
            local_git_folder = dest_folder / local_git_folder_name

            if verbose:
                logger.debug("git address for coding is: {}", git_addr)
                logger.debug("local git folder name is : {}", local_git_folder_name)

            # do git checkout
            update_git(git_addr, local_git_folder)
