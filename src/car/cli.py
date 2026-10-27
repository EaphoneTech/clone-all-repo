from __future__ import annotations

import concurrent.futures
import importlib
import os
import sys
from collections.abc import Callable
from functools import partial
from pathlib import Path

import click
import yaml
from loguru import logger
from tqdm import tqdm

from .git_ops import push_to_remote, update_git
from .refspec import sync_config

SupportsFunc = Callable[[str], bool]
GetUrlFunc = Callable[[str], str]
GetLocalPathFunc = Callable[[str, Path], Path]

REGISTRY: list = []

PARALLEL_ENV = "CAR_PARALLEL"
# CI 环境通常都会设置 CI=true, 此时进度条没有意义
PROGRESS_ENV = "CI"

_FALSY_VALUES = {"", "0", "false", "no", "off"}


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


def process_single_repo(
    repo_config: dict,
    dest_folder: Path,
    defaults: dict | None = None,
) -> tuple[str, bool]:
    """处理单个仓库的函数，用于并行执行。

    Returns:
        (仓库标识, 是否成功)
    """
    label = str(repo_config.get("repo", "<unknown>"))

    try:
        repo_url, local_path = determine_site_plugin(label, dest_folder)
        if repo_url is None or local_path is None:
            logger.warning("没有匹配的插件, 跳过: {}", label)
            return label, False

        config = sync_config(defaults, repo_config)

        # 首先更新本地 git 仓库, 抓取失败时不推送, 避免用陈旧数据覆盖远端
        if not update_git(repo_url, local_path, config.ref_filter):
            return label, False

        # 其次，如果有 to 的话，还要推给 to
        to = repo_config.get("to")
        if to is None:
            return label, True

        to_url, _ = determine_site_plugin(to, dest_folder)
        if to_url is None:
            logger.warning("没有匹配的插件, 跳过推送目标: {}", to)
            return label, False

        return label, push_to_remote(local_path, to_url, config)

    except Exception as exc:  # 单仓库失败不应中断其它仓库
        logger.exception("处理 {} 时发生未预期错误: {}", label, exc)
        return label, False


def _resolve_parallel(cli_value: int | None, defaults: dict | None) -> int:
    """并行度优先级: 命令行 > 环境变量 > repos.yaml defaults > 1。"""
    if cli_value is not None:
        return max(1, int(cli_value))

    env_value = os.environ.get(PARALLEL_ENV)
    if env_value:
        try:
            return max(1, int(env_value))
        except ValueError:
            logger.warning("{} 不是合法的整数: {}", PARALLEL_ENV, env_value)

    raw = (defaults or {}).get("parallel", 1)
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        logger.warning("defaults.parallel 不是合法的整数: {}", raw)
        return 1


def _as_bool(value: object) -> bool:
    if isinstance(value, str):
        return value.strip().lower() not in _FALSY_VALUES
    return bool(value)


def _env_flag(name: str) -> bool | None:
    """读取布尔型环境变量, 未设置时返回 None。"""
    raw = os.environ.get(name)
    if raw is None:
        return None
    return _as_bool(raw)


def _resolve_progress(cli_value: bool | None, defaults: dict | None) -> bool:
    """是否显示进度条。

    优先级: 命令行 > repos.yaml 的 defaults.progress > CI 环境变量 > 默认开启。
    """
    if cli_value is not None:
        return bool(cli_value)

    configured = (defaults or {}).get("progress")
    if configured is not None:
        return _as_bool(configured)

    ci = _env_flag(PROGRESS_ENV)
    if ci is not None:
        return not ci

    return True


def main(
    repos_yaml_file: Path,
    dest_folder: Path,
    parallel: int | None = None,
    progress: bool | None = None,
    verbose: bool = False,
):
    # 先读 repos.yaml
    if not repos_yaml_file.exists():
        logger.error("repos.yaml 文件不存在，请检查文件是否存在")
        sys.exit(1)

    with open(repos_yaml_file, encoding="utf-8") as f:
        repos_dict = yaml.safe_load(f) or {}

    defaults = repos_dict.get("defaults") or {}
    repos = repos_dict.get("repos") or []

    # 初始化日志
    show_progress = _resolve_progress(progress, defaults)
    if show_progress:
        logger.remove()
        logger.add(lambda msg: tqdm.write(msg, end=""), colorize=True)

    # 确保目标文件夹存在
    if not dest_folder.exists():
        dest_folder.mkdir(parents=True, exist_ok=True)
        gitignore_file = dest_folder / ".gitignore"
        if not gitignore_file.exists():
            gitignore_file.write_text("*")

    register_all_modules()

    workers = _resolve_parallel(parallel, defaults)

    logger.debug("使用 {} 个并发处理 {} 个仓库", workers, len(repos))
    if not show_progress:
        logger.debug("进度条已关闭")

    # 创建处理单个仓库的函数
    process_repo_partial = partial(
        process_single_repo, dest_folder=dest_folder, defaults=defaults
    )

    # 使用线程池并行处理
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        gen = executor.map(process_repo_partial, repos)

        if show_progress:
            gen = tqdm(
                gen,
                total=len(repos),
                desc="Processing repositories",
            )

        results = list(gen)

    failed = [name for name, ok in results if not ok]
    if failed:
        logger.error(
            "{} / {} 个仓库同步失败: {}",
            len(failed),
            len(results),
            ", ".join(failed),
        )
        sys.exit(1)

    logger.info("全部 {} 个仓库同步完成", len(results))


@click.command()
@click.argument(
    "config_file",
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
    help="本地 git 仓库的路径",
    show_default=True,
)
@click.option(
    "--parallel",
    "-p",
    type=int,
    required=False,
    default=None,
    help=f"并行处理的数量 (默认取 ${PARALLEL_ENV} 或 repos.yaml 的 defaults.parallel, 否则 1)",
)
@click.option(
    "--progress/--no-progress",
    type=bool,
    is_flag=True,
    required=False,
    default=None,
    help=(
        "是否显示进度条, 默认取 repos.yaml 的 defaults.progress, "
        f"CI 环境 (${PROGRESS_ENV}) 下自动关闭"
    ),
)
@click.option(
    "--verbose",
    "-v",
    type=bool,
    is_flag=True,
    required=False,
    default=False,
    help="是否打印更详细的日志",
    show_default=True,
)
def click_main(
    config_file: Path = Path("./repos.yaml"),
    output_dir: Path = Path("./repos/"),
    parallel: int | None = None,
    progress: bool | None = None,
    verbose: bool = False,
):
    """批量 clone 和 push git 仓库

    CONFIG_FILE 默认是 repos.yaml
    """

    main(config_file, output_dir, parallel=parallel, progress=progress, verbose=verbose)
