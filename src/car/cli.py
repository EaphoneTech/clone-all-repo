import importlib
import sys
from pathlib import Path

import yaml
from loguru import logger
from rich.progress import track


def main(repos_yaml_file: Path, dest_folder: Path, verbose: bool = False):
    # 先读 repos.yaml
    if not repos_yaml_file.exists():
        logger.error("repos.yaml 文件不存在，请检查文件是否存在")
        sys.exit(1)

    # 确保目标文件夹存在
    if not dest_folder.exists():
        dest_folder.mkdir(parents=True, exist_ok=True)

    with open(repos_yaml_file, encoding="utf-8") as f:
        repos_dict = yaml.safe_load(f)

    # 看一共有几个 repo
    for site in track(repos_dict["sites"]):
        # 根据每个 sites, 动态导入 car.sites.xxx 来处理
        site_name = site["site"]
        try:
            site_module = importlib.import_module(f"car.sites.{site_name}")

        except ImportError:
            logger.error("car.sites.{} 模块不存在", site_name)
            continue

        site_module.process(site, dest_folder, verbose=verbose)
