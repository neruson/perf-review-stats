```
> python stats.py
Calculating stats between 2020-02-01 and 2021-02-01...
PR comments left: 89
PRs merged: 267
Tickets closed: 173
```

Requires `requests` and `python-dateutil`.

Set the following environment variables to make it work:

- `GITHUB_USERNAME`: Your GitHub username
- `GITHUB_API_TOKEN`: Personal access token with "repo" scope. Create one here: https://github.com/settings/tokens
- `JIRA_USERNAME`: Your Jira username, generally your email address
- `JIRA_API_TOKEN`: API token for Atlassian. Create one here: https://id.atlassian.com/manage-profile/security/api-tokens
