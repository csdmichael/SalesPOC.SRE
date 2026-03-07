"""GitHub repository connector for SRE monitoring."""

import logging
from dataclasses import dataclass

from github import Auth, Github, GithubException

from src.config import GITHUB_REPOS, settings

logger = logging.getLogger(__name__)


@dataclass
class RepoStatus:
    """Status of a connected GitHub repository."""

    name: str
    url: str
    component: str
    connected: bool
    default_branch: str | None = None
    open_issues: int = 0
    last_commit_sha: str | None = None
    last_commit_message: str | None = None
    error: str | None = None


class GitHubConnector:
    """Connects to and monitors GitHub repositories."""

    def __init__(self, token: str | None = None):
        gh_token = token or settings.github_token
        if gh_token:
            self._client = Github(auth=Auth.Token(gh_token))
        else:
            self._client = Github()
        self._repos = GITHUB_REPOS
        logger.info("GitHub connector initialized for %d repos.", len(self._repos))

    def get_repo_status(self, repo_full_name: str) -> RepoStatus:
        """Get status of a single repository."""
        repo_cfg = next(
            (r for r in self._repos if f"{settings.github_org}/{r['name']}" == repo_full_name),
            None,
        )
        if not repo_cfg:
            return RepoStatus(
                name=repo_full_name, url="", component="unknown",
                connected=False, error="Not in monitored list",
            )
        try:
            repo = self._client.get_repo(repo_full_name)
            branch = repo.get_branch(repo.default_branch)
            return RepoStatus(
                name=repo_cfg["name"],
                url=repo_cfg["url"],
                component=repo_cfg["component"],
                connected=True,
                default_branch=repo.default_branch,
                open_issues=repo.open_issues_count,
                last_commit_sha=branch.commit.sha[:7],
                last_commit_message=branch.commit.commit.message.split("\n")[0],
            )
        except GithubException as exc:
            logger.error("Failed to connect to %s: %s", repo_full_name, exc)
            return RepoStatus(
                name=repo_cfg["name"], url=repo_cfg["url"],
                component=repo_cfg["component"],
                connected=False, error=str(exc),
            )

    def get_all_statuses(self) -> list[RepoStatus]:
        """Get status of all monitored repositories."""
        statuses = []
        for repo_cfg in self._repos:
            full_name = f"{settings.github_org}/{repo_cfg['name']}"
            statuses.append(self.get_repo_status(full_name))
        return statuses

    def check_connectivity(self) -> dict:
        """Quick connectivity check for all repos."""
        statuses = self.get_all_statuses()
        connected = [s for s in statuses if s.connected]
        failed = [s for s in statuses if not s.connected]
        return {
            "total": len(statuses),
            "connected": len(connected),
            "failed": len(failed),
            "repos": {s.name: s.connected for s in statuses},
            "errors": {s.name: s.error for s in failed if s.error},
        }
