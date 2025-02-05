from pathlib import Path

import click

from car.cli import main


@click.command()
def click_main():
    # 各个参数
    repos_yaml_file = Path("./repos.yaml")
    dest_folder = Path("./repos/")
    verbose: bool = False

    main(repos_yaml_file, dest_folder, verbose=verbose)


if __name__ == "__main__":
    click_main()
