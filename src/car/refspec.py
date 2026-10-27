"""ref 选择配置的解析与推送计划计算。

repos.yaml 中的 ``defaults`` 提供全局默认值, 单个仓库可以用 ``refs`` (或
同名顶层键) 覆盖。这里只做纯逻辑, 不接触网络和磁盘, 方便单独验证。
"""

from __future__ import annotations

import fnmatch
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from typing import TypeVar

HEADS_PREFIX = "refs/heads/"
TAGS_PREFIX = "refs/tags/"
PULL_PREFIX = "refs/pull/"

ALL = "all"
NONE = "none"
PATTERNS = "patterns"

DEFAULT_BATCH_SIZE = 50

_SELECTION_KEYS = ("branches", "tags", "pull_refs")
_SCALAR_KEYS = ("prune", "batch_size")
_SELECTION_KINDS = (ALL, NONE, PATTERNS)

T = TypeVar("T")


@dataclass(frozen=True)
class Selection:
    """单个 ref 命名空间的选择规则。

    kind 为 all / none / patterns 之一; patterns 中的模式相对命名空间前缀
    (例如 branches 的 ``release/*`` 实际匹配 ``refs/heads/release/*``),
    使用 fnmatch 语义, ``*`` 可以跨越 ``/``。
    """

    kind: str = ALL
    patterns: tuple[str, ...] = ()

    def __post_init__(self):
        if self.kind not in _SELECTION_KINDS:
            raise ValueError(f"未知的 ref 选择类型: {self.kind!r}")

    def hit(self, relative_ref: str) -> bool:
        if self.kind == ALL:
            return True
        if self.kind == NONE:
            return False
        return any(
            fnmatch.fnmatchcase(relative_ref, pattern) for pattern in self.patterns
        )


def _expand_pull_patterns(selection: Selection) -> Selection:
    """让 ``pull_refs: [1234]`` 也能匹配 ``refs/pull/1234/head``。"""
    if selection.kind != PATTERNS:
        return selection

    patterns = tuple(
        f"{pattern}/*" if pattern.isdigit() else pattern
        for pattern in selection.patterns
    )
    return Selection(PATTERNS, patterns)


@dataclass(frozen=True)
class RefFilter:
    """三个命名空间的选择规则, 决定哪些 ref 参与同步。"""

    branches: Selection = Selection(ALL)
    tags: Selection = Selection(ALL)
    pull_refs: Selection = Selection(NONE)

    def __post_init__(self):
        expanded = _expand_pull_patterns(self.pull_refs)
        if expanded is not self.pull_refs:
            object.__setattr__(self, "pull_refs", expanded)

    @property
    def want_pull_refs(self) -> bool:
        return self.pull_refs.kind != NONE

    def matches(self, ref: str) -> bool:
        if ref.startswith(HEADS_PREFIX):
            return self.branches.hit(ref[len(HEADS_PREFIX) :])
        if ref.startswith(TAGS_PREFIX):
            return self.tags.hit(ref[len(TAGS_PREFIX) :])
        if ref.startswith(PULL_PREFIX):
            return self.pull_refs.hit(ref[len(PULL_PREFIX) :])
        return False


@dataclass(frozen=True)
class SyncConfig:
    """单个仓库的完整同步配置。"""

    ref_filter: RefFilter = RefFilter()
    prune: bool = False
    batch_size: int = DEFAULT_BATCH_SIZE


def parse_selection(value: object) -> Selection:
    """把 YAML 里的取值解析成 Selection。

    - ``all`` / ``none`` (大小写不敏感)
    - 单个模式字符串
    - 模式列表 (空列表等价于 none)
    """
    if value is None:
        return Selection(NONE)

    if isinstance(value, str):
        text = value.strip()
        lowered = text.lower()
        if lowered == ALL:
            return Selection(ALL)
        if lowered == NONE:
            return Selection(NONE)
        if not text:
            return Selection(NONE)
        return Selection(PATTERNS, (text,))

    if isinstance(value, (list, tuple)):
        patterns = tuple(str(item).strip() for item in value if str(item).strip())
        if not patterns:
            return Selection(NONE)
        return Selection(PATTERNS, patterns)

    raise ValueError(f"无法解析的 ref 选择配置: {value!r}")


def _flatten(raw: object) -> dict:
    """把 defaults / 单仓库配置摊平成同一层的键值。"""
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise ValueError(f"配置必须是映射类型: {raw!r}")

    flat = {key: raw[key] for key in (*_SELECTION_KEYS, *_SCALAR_KEYS) if key in raw}

    refs = raw.get("refs")
    if refs is not None:
        if not isinstance(refs, Mapping):
            raise ValueError(f"refs 必须是映射类型: {refs!r}")
        for key in _SELECTION_KEYS:
            if key in refs:
                flat[key] = refs[key]

    return flat


def _positive_int(value: object, default: int) -> int:
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return default


def sync_config(
    defaults: Mapping | None = None,
    repo_config: Mapping | None = None,
) -> SyncConfig:
    """合并全局默认与单仓库配置 (单仓库优先, 列表值整体替换)。"""
    merged = {**_flatten(defaults), **_flatten(repo_config)}

    return SyncConfig(
        ref_filter=RefFilter(
            branches=parse_selection(merged.get("branches", ALL)),
            tags=parse_selection(merged.get("tags", ALL)),
            pull_refs=parse_selection(merged.get("pull_refs", NONE)),
        ),
        prune=bool(merged.get("prune", False)),
        batch_size=_positive_int(merged.get("batch_size"), DEFAULT_BATCH_SIZE),
    )


@dataclass
class SyncPlan:
    """一次同步需要执行的动作。"""

    push: list[str] = field(default_factory=list)
    delete: list[str] = field(default_factory=list)
    up_to_date: int = 0
    ignored: int = 0
    remote_only: list[str] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        return not self.push and not self.delete


def build_plan(
    ref_filter: RefFilter,
    remote_refs: Mapping[str, str],
    local_refs: Mapping[str, str],
    prune: bool = False,
) -> SyncPlan:
    """比较远端与本地 ref, 得出要推送和要删除的清单。

    删除范围严格限定为: 远端存在 + 命中本次选择规则 + 本地不存在。
    未命中选择规则的远端 ref 永远不会被删除, 避免把仓库从 "全量" 降级为
    "重点分支" 时误删其余分支。
    """
    plan = SyncPlan()

    for ref in sorted(remote_refs):
        if not ref_filter.matches(ref):
            plan.ignored += 1
            continue

        local_oid = local_refs.get(ref)
        if local_oid is None:
            if prune:
                plan.delete.append(ref)
            else:
                plan.remote_only.append(ref)
        elif local_oid != remote_refs[ref]:
            plan.push.append(ref)
        else:
            plan.up_to_date += 1

    for ref in sorted(local_refs):
        if ref_filter.matches(ref) and ref not in remote_refs:
            plan.push.append(ref)

    return plan


def chunked(items: Iterable[T], size: int) -> Iterator[list[T]]:
    """按固定大小切批, size 至少为 1。"""
    step = max(1, size)
    batch: list[T] = []
    for item in items:
        batch.append(item)
        if len(batch) >= step:
            yield batch
            batch = []
    if batch:
        yield batch
