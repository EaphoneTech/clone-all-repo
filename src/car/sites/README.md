# sites

在这里每个 .py 的规则是:


- py 的名字对应 `repos.yaml` 中的 `site` 的内容
- `process(site: dict, dest_folder: Path, verbose: bool = False)` 函数应当读取 `site` 中的配置，并进行对应的处理
