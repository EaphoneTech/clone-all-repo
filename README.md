# clone-all-repo

a python utility that clones multiple git repo

## Configuration

Configuration is done by `repos.yaml`:

```yaml
# repos.yaml
sites:
  - site: github
    org: <github_org_name>
    repos:
      - <github_repo_name>
  - site: coding
    team: <coding_team_name>
    projects:
      - project: <coding_project_name>
        repos:
          - <coding_repo_name>
```
