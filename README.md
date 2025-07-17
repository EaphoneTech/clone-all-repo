# clone-all-repo

a python utility that clones multiple git repo, and optionally push to another location.

## Configuration

Configuration is done by `repos.yaml`:

```yaml
#repos.yaml

repos:
- repo: github/<github_org_name>/<github_repo_name>
  to: cnb/<cnb_org_name>/<cnb_sub_org_name>/<cnb_repo_name>
- repo: coding/<coding_team_name>/<coding_project_name>/<coding_repo_name>
  to: https://xxx.xxx/xxx.git
```
