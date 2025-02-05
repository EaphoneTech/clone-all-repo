from pathlib import Path
from car.cli import main

if __name__ == "__main__":
    # 各个参数
    repos_yaml_file = Path("./repos.yaml")
    dest_folder = Path("./repos/")
    verbose: bool = False

    main(repos_yaml_file, dest_folder, verbose=verbose)
