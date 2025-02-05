from pathlib import Path

from ..git_ops import update_git


def process(site: dict, dest_folder: Path, verbose: bool = False):
    org_name = site["org"]
    repos = site["repos"]
    for repo_name in repos:
        git_addr = f"https://github.com/{org_name}/{repo_name}.git"

        if verbose:
            print(f"git address for github is: {git_addr}")

        local_git_folder_name = f"github/{org_name}/{repo_name}"
        local_git_folder = dest_folder / local_git_folder_name

        if verbose:
            print(f"git address for coding is: {git_addr}")
            print(f"local git folder name is : {local_git_folder_name}")

        # do git checkout
        update_git(git_addr, local_git_folder)
