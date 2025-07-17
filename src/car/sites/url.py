import re
from pathlib import Path


def supports(url: str) -> bool:
    return (
        url.startswith("https://")
        or url.startswith("http://")
        or url.startswith("ssh://")
    )


def get_url(url: str) -> str:
    return url


def get_local_path(url: str, base_dir: Path) -> Path:
    """试图从一般的 https://xxx.git 中找出能够表示仓库名字的部分

    例如: https://common.com/group/repo.git 应该返回 group/repo

    Args:
        url (str):
        base_dir (Path):

    Returns:
        Path:
    """
    # 去除 .git 后缀
    if url.endswith(".git"):
        url = url[: -len(".git")]

    # 处理 SSH 格式：git@xxx.com:group/repo
    ssh_pattern = re.compile(r"^git@([^:/]+)[/:](.+)$")
    ssh_match = ssh_pattern.match(url)
    if ssh_match:
        _, path_part = ssh_match.groups()
        parts = path_part.strip("/").split("/")
        if len(parts) >= 2:
            group_name, repo_name = parts[-2], parts[-1]
        elif len(parts) == 1:
            group_name = "default"
            repo_name = parts[0]
        else:
            raise ValueError(f"Invalid SSH URL: {url}")
        return base_dir / group_name / repo_name

    # 处理 HTTPS/HTTP/GIT 等格式
    from urllib.parse import urlparse

    parsed = urlparse(url)
    path_part = parsed.path.strip("/")

    if not path_part:
        raise ValueError(f"URL 中未包含有效的路径信息: {url}")

    parts = path_part.split("/")
    if len(parts) >= 2:
        group_name, repo_name = parts[-2], parts[-1]
    elif len(parts) == 1:
        group_name = "default"
        repo_name = parts[0]
    else:
        raise ValueError(f"无法解析 URL 路径: {url}")

    return base_dir / group_name / repo_name
