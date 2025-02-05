from pathlib import Path
import yaml
import sys
from rich.progress import track
import importlib


def main(repos_yaml_file: Path, dest_folder: Path, verbose: bool = False):
    # 先读 repos.yaml
    if not repos_yaml_file.exists():
        print("repos.yaml 文件不存在，请检查文件是否存在", file=sys.stderr)
        sys.exit(1)

    # 确保目标文件夹存在
    if not dest_folder.exists():
        dest_folder.mkdir(parents=True, exist_ok=True)

    with open(repos_yaml_file, "r", encoding="utf-8") as f:
        repos_dict = yaml.safe_load(f)

    # 看一共有几个 repo
    for site in track(repos_dict["sites"]):
        # TODO: 根据每个 sites, 动态导入 car.sites.xxx 来处理
        site_name = site["site"]
        try:
            site_module = importlib.import_module(f"car.sites.{site_name}")

        except ImportError:
            print(f"car.sites.{site_name} 模块不存在", file=sys.stderr)
            continue

        site_module.process(site, dest_folder, verbose=verbose)

    # TODO: 根据 repos.yaml 中的
