"""本地仓库的抓取与推送。

设计要点:
- 只同步 refs/heads 与 refs/tags (可选 refs/pull), 不再使用 ``--mirror``
  的全命名空间语义, 避免把上游数千个 PR ref 卷进每次推送。
- 推送前先 ``ls-remote`` 对账, 只推远端缺失或落后的 ref, 实现断点续推。
- 分批发 refspec, 单次请求体量与仓库历史规模解耦。
- 删除只针对"远端存在 + 命中本次选择 + 本地不存在"的 ref, 且单独执行、
  失败仅告警, 不允许影响更新。
"""

from __future__ import annotations

from pathlib import Path

from git import GitCommandError, InvalidGitRepositoryError, PushInfo, Repo
from loguru import logger

from .refspec import (
    HEADS_PREFIX,
    PULL_PREFIX,
    TAGS_PREFIX,
    RefFilter,
    SyncConfig,
    build_plan,
    chunked,
)

PUSH_REMOTE_NAME = "push-remote"
ORIGIN_REMOTE_NAME = "origin"

_PUSH_ERROR_FLAGS = (
    PushInfo.ERROR
    | PushInfo.REJECTED
    | PushInfo.REMOTE_REJECTED
    | PushInfo.REMOTE_FAILURE
)

_LOG_LIMIT = 600


def _brief(exc: BaseException, limit: int = _LOG_LIMIT) -> str:
    """把 git 的错误压成单行, 便于日志阅读 (403 的响应体可能很长)。"""
    text = getattr(exc, "stderr", None) or str(exc)
    text = " ".join(part.strip() for part in str(text).splitlines() if part.strip())
    return text[:limit]


def _get_remote(repo: Repo, name: str, url: str, *, create: bool = True):
    for remote in repo.remotes:
        if remote.name == name:
            if remote.url != url:
                logger.debug("将 {} 的 url 更新为 {}", name, url)
                remote.set_url(url)
            return remote

    if not create:
        return None

    logger.debug("添加远程仓库 {} 为 {}", name, url)
    return repo.create_remote(name, url)


def _fetch_refspecs(ref_filter: RefFilter) -> list[str]:
    specs = [
        f"+{HEADS_PREFIX}*:{HEADS_PREFIX}*",
        f"+{TAGS_PREFIX}*:{TAGS_PREFIX}*",
    ]
    if ref_filter.want_pull_refs:
        specs.append(f"+{PULL_PREFIX}*:{PULL_PREFIX}*")
    return specs


def _configure_fetch_refspec(repo: Repo, specs: list[str]) -> None:
    """把 origin 的 fetch refspec 收敛到需要的命名空间。

    老版本的仓库是 ``--mirror`` 克隆出来的, ``remote.origin.fetch`` 为
    ``+refs/*:refs/*``; 每次运行都必须重写, 否则会继续把 PR ref 拉进本地。
    """
    repo.git.config("--replace-all", "remote.origin.fetch", specs[0])
    for spec in specs[1:]:
        repo.git.config("--add", "remote.origin.fetch", spec)


def _purge_local_refs(repo: Repo, prefix: str) -> int:
    """删除本地某个命名空间下的全部 ref, 返回删除数量。"""
    output = repo.git.for_each_ref("--format=%(refname)", prefix)
    names = [line.strip() for line in output.splitlines() if line.strip()]
    for name in names:
        repo.git.update_ref("-d", name)
    return len(names)


def _open_or_clone(git_repo_url: str, local_dir: Path) -> Repo | None:
    if local_dir.exists():
        try:
            return Repo(local_dir)
        except InvalidGitRepositoryError:
            if any(local_dir.iterdir()):
                logger.error(
                    "{} 不是 git 仓库且非空, 跳过: {}", local_dir, git_repo_url
                )
                return None

    local_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Cloning {} to {}", git_repo_url, local_dir)
    try:
        return Repo.clone_from(git_repo_url, local_dir, bare=True)
    except GitCommandError as exc:
        logger.error("克隆 {} 失败: {}", git_repo_url, _brief(exc))
        return None


def update_git(
    git_repo_url: str,
    local_dir: Path,
    ref_filter: RefFilter | None = None,
) -> bool:
    """把远端仓库抓到 local_dir。

    Args:
        git_repo_url: 远程 Git 仓库地址
        local_dir: 本地存储路径
        ref_filter: ref 选择规则, 决定是否抓取 refs/pull

    Returns:
        是否成功
    """
    filter_ = ref_filter or RefFilter()
    repo = _open_or_clone(git_repo_url, local_dir)
    if repo is None:
        return False

    if not repo.bare:
        logger.warning("{} 不是 bare 仓库, 会继续使用已检出的 refs", local_dir)

    _get_remote(repo, ORIGIN_REMOTE_NAME, git_repo_url)

    if not filter_.want_pull_refs:
        dropped = _purge_local_refs(repo, PULL_PREFIX)
        if dropped:
            logger.info("清理本地 refs/pull 共 {} 个", dropped)

    specs = _fetch_refspecs(filter_)
    _configure_fetch_refspec(repo, specs)

    logger.debug("Pulling latest changes for {}", git_repo_url)
    try:
        # 显式传 refspec, 不依赖 GitPython 缓存的 remote 配置
        repo.git.fetch("--prune", ORIGIN_REMOTE_NAME, *specs)
    except GitCommandError as exc:
        logger.error("拉取仓库 {} 时发生错误: {}", git_repo_url, _brief(exc))
        return False

    logger.info("Successfully fetched latest changes.")
    return True


def _parse_ls_remote(output: str) -> dict[str, str]:
    refs: dict[str, str] = {}
    for line in output.splitlines():
        line = line.strip()
        if not line or line.endswith("^{}"):
            # 跳过 annotated tag 的 peel 行
            continue
        parts = line.split("\t") if "\t" in line else line.split(maxsplit=1)
        if len(parts) != 2:
            continue
        oid, ref = parts[0].strip(), parts[1].strip()
        refs[ref] = oid
    return refs


def _fetch_remote_refs(
    repo: Repo,
    git_remote_url: str,
    ref_filter: RefFilter,
) -> dict[str, str]:
    refs = _parse_ls_remote(repo.git.ls_remote("--heads", "--tags", git_remote_url))
    if ref_filter.want_pull_refs:
        refs.update(
            _parse_ls_remote(repo.git.ls_remote(git_remote_url, f"{PULL_PREFIX}*"))
        )
    return refs


def _local_refs(repo: Repo, ref_filter: RefFilter) -> dict[str, str]:
    patterns = [HEADS_PREFIX, TAGS_PREFIX]
    if ref_filter.want_pull_refs:
        patterns.append(PULL_PREFIX)

    output = repo.git.for_each_ref("--format=%(objectname) %(refname)", *patterns)
    refs: dict[str, str] = {}
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        oid, _, ref = line.partition(" ")
        if oid and ref:
            refs[ref] = oid
    return refs


def _push_refspecs(remote, refspecs: list[str]) -> tuple[bool, str]:
    """推送一批 refspec, 返回 (是否全部成功, 失败详情)。"""
    try:
        # GitPython 的 push 只接受一个 refspec 参数 (str 或 list)
        infos = remote.push(refspecs)
    except GitCommandError as exc:
        return False, _brief(exc)

    problems = [
        str(info.summary) for info in (infos or []) if info.flags & _PUSH_ERROR_FLAGS
    ]
    if problems:
        return False, "; ".join(problems[:5])
    return True, ""


def _push_refs(remote, refs: list[str], batch_size: int) -> list[str]:
    """分批推送 ref, 返回最终仍然失败的 ref 列表。

    某批失败时逐个重试, 既能确认其中已经成功的部分, 也能把日志精确到
    具体是哪个 ref 被拒绝 (定位 403 根因时很关键)。
    """
    failed: list[str] = []

    for batch in chunked(refs, batch_size):
        refspecs = [f"+{ref}:{ref}" for ref in batch]
        ok, detail = _push_refspecs(remote, refspecs)
        if ok:
            continue

        logger.error("一批 {} 个 ref 推送失败: {}", len(batch), detail)
        failed.extend(batch)

        if len(batch) == 1:
            continue

        for ref in list(batch):
            ok_one, detail_one = _push_refspecs(remote, [f"+{ref}:{ref}"])
            if ok_one:
                failed.remove(ref)
            else:
                logger.error("  ref {} 推送失败: {}", ref, detail_one)

    return failed


def _delete_refs(remote, refs: list[str], batch_size: int) -> None:
    """删除远端 ref, 失败只告警 (删除是最容易被服务端策略拒绝的操作)。"""
    for batch in chunked(refs, batch_size):
        try:
            remote.push([f":{ref}" for ref in batch])
        except GitCommandError as exc:
            logger.warning(
                "删除 {} 个远端 ref 失败(已忽略): {}", len(batch), _brief(exc)
            )


def push_to_remote(
    local_git_folder: Path,
    git_remote_url: str,
    config: SyncConfig | None = None,
) -> bool:
    """把本地仓库中符合选择规则的 ref 推送到指定远端。

    Args:
        local_git_folder: 本地 Git 仓库路径
        git_remote_url: 要推送的远程仓库地址
        config: 同步配置 (ref 选择 / prune / 分批大小)

    Returns:
        是否全部成功
    """
    sync = config or SyncConfig()
    name = local_git_folder.stem

    if not local_git_folder.exists():
        logger.error("本地仓库路径不存在: {}", local_git_folder)
        return False

    try:
        repo = Repo(local_git_folder)
    except InvalidGitRepositoryError:
        logger.error("指定的路径不是一个 Git 仓库: {}", local_git_folder)
        return False

    push_remote = _get_remote(repo, PUSH_REMOTE_NAME, git_remote_url)

    try:
        remote_refs = _fetch_remote_refs(repo, git_remote_url, sync.ref_filter)
    except GitCommandError as exc:
        logger.error("读取远端 {} 的 ref 失败: {}", git_remote_url, _brief(exc))
        return False

    local_refs = _local_refs(repo, sync.ref_filter)
    plan = build_plan(sync.ref_filter, remote_refs, local_refs, sync.prune)

    logger.info(
        "{}: 本地 {} 个 ref, 远端 {} 个, 待推送 {}, 待删除 {}, 已一致 {}",
        name,
        len(local_refs),
        len(remote_refs),
        len(plan.push),
        len(plan.delete),
        plan.up_to_date,
    )
    if plan.remote_only:
        preview = ", ".join(plan.remote_only[:5])
        logger.warning(
            "{}: {} 个 ref 在远端存在但本地没有 (不会推送): {}{}",
            name,
            len(plan.remote_only),
            preview,
            " ..." if len(plan.remote_only) > 5 else "",
        )

    failed = _push_refs(push_remote, plan.push, sync.batch_size)

    if plan.delete:
        logger.info("{}: 删除远端残留 ref {} 个", name, len(plan.delete))
        _delete_refs(push_remote, plan.delete, sync.batch_size)

    if failed:
        logger.error("{}: 仍有 {} 个 ref 推送失败", name, len(failed))
        return False

    logger.info("{}: 同步完成 ({})", name, git_remote_url)
    return True
