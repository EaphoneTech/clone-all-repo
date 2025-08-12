import importlib
import sys
from collections.abc import Callable
from pathlib import Path

import click
import yaml
from loguru import logger
from tqdm import tqdm

from .git_ops import push_to_remote, update_git

SupportsFunc = Callable[[str], bool]
GetUrlFunc = Callable[[str], str]
GetLocalPathFunc = Callable[[str, Path], Path]

REGISTRY: list = []


# 注册所有 module
def register_all_modules():
    global REGISTRY
    for module_file in (Path(__file__).parent / "sites").glob("*.py"):
        if module_file.stem != "url":
            REGISTRY.append(importlib.import_module(f"car.sites.{module_file.stem}"))
            logger.debug("registered plugin {}", module_file.stem)

    # 将 url 放在最后
    REGISTRY.append(importlib.import_module("car.sites.url"))
    logger.debug("registered plugin {}", "url")


def determine_site_plugin(
    full_addr: str, dest_folder: Path
) -> tuple[str, Path] | tuple[None, None]:
    """
    统一入口：根据 full_addr 自动判断使用哪个插件
    返回值示例:
        {
            "url": "https://github.com/user/repo.git",
            "local_path": Path("/tmp/repos/repo")
        }
    """

    for plugin in REGISTRY:
        get_url_func: GetUrlFunc = plugin.get_url
        get_local_path_func: GetLocalPathFunc = plugin.get_local_path
        supports_func: SupportsFunc = plugin.supports
        if supports_func(full_addr):
            return get_url_func(full_addr), get_local_path_func(full_addr, dest_folder)

    return None, None


def main(repos_yaml_file: Path, dest_folder: Path, verbose: bool = False):
    # 先读 repos.yaml
    if not repos_yaml_file.exists():
        logger.error("repos.yaml 文件不存在，请检查文件是否存在")
        sys.exit(1)

    # 确保目标文件夹存在
    if not dest_folder.exists():
        dest_folder.mkdir(parents=True, exist_ok=True)

    register_all_modules()

    with open(repos_yaml_file, encoding="utf-8") as f:
        repos_dict = yaml.safe_load(f)

    # 看一共有几个 repo
    for repo in tqdm(repos_dict["repos"]):
        repo_url, local_path = determine_site_plugin(repo.get("repo", ""), dest_folder)

        if repo_url is None or local_path is None:
            continue

        # 首先更新本地 git 仓库
        update_git(repo_url, local_path)

        # 其次，如果有 to 的话，还要推给 to

        to = repo.get("to")
        if to is not None:
            to_url, _ = determine_site_plugin(to, dest_folder)

            if to_url is not None:
                push_to_remote(local_path, to_url)


@click.command()
@click.argument(
    "input",
    type=click.Path(file_okay=True, dir_okay=False, path_type=Path),
    required=False,
    default="repos.yaml",
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    required=False,
    default="repos",
)
@click.option("--verbose", "-v", type=bool, is_flag=True, required=False, default=False)
def click_main(
    input: Path = Path("./repos.yaml"),
    output_dir: Path = Path("./repos/"),
    verbose: bool = False,
):
    main(input, output_dir, verbose=verbose)
