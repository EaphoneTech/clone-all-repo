from pathlib import Path

import click

from car.cli import main


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


if __name__ == "__main__":
    click_main()
