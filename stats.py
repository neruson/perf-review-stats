from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, List, Optional, Tuple, TypeVar

import requests
from dateutil.parser import isoparse

Obj = TypeVar("Obj")
Cursor = TypeVar("Cursor")

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
JIRA_SEARCH_URL = "https://urbanairship.atlassian.net/rest/api/latest/search"

github_username = os.getenv("GITHUB_USERNAME", "")
github_api_token = os.getenv("GITHUB_API_TOKEN", "")
jira_username = os.getenv("JIRA_USERNAME", "")
jira_api_token = os.getenv("JIRA_API_TOKEN", "")


def github_auth() -> Tuple[str, str]:
    return (github_username, github_api_token)


def jira_auth() -> Tuple[str, str]:
    return (jira_username, jira_api_token)


@dataclass
class Comment:
    cursor: str
    repository: str
    created_at: datetime

    @classmethod
    def from_dict(cls, data: dict) -> Comment:
        return cls(
            cursor=data["cursor"],
            repository=data["node"]["repository"]["nameWithOwner"],
            created_at=isoparse(data["node"]["createdAt"]),
        )


def get_comments(after: Optional[str] = None) -> List[Comment]:
    query = """
        query($after:String) {
            viewer {
                issueComments(
                    after:$after,
                    first:100,
                    orderBy: {field:UPDATED_AT, direction:DESC}
                ) {
                    edges {
                        cursor
                        node {
                            repository {
                                nameWithOwner
                            }
                            createdAt
                        }
                    }
                }
            }
        }
    """
    variables = {"after": after}
    response = requests.post(
        url=GITHUB_GRAPHQL_URL,
        json={"query": query, "variables": variables},
        auth=github_auth(),
    )
    response.raise_for_status()
    data = response.json()
    return [
        Comment.from_dict(d) for d in data["data"]["viewer"]["issueComments"]["edges"]
    ]


def get_comment_date(comment: Comment) -> datetime:
    return comment.created_at


def get_comment_cursor(comment: Comment) -> str:
    return comment.cursor


def get_all(
    get_objects: Callable[[Optional[Cursor]], List[Obj]],
    get_date: Callable[[Obj], datetime],
    get_cursor: Callable[[Obj], Cursor],
) -> Callable[[datetime, datetime], List[Obj]]:
    def func(start: datetime, end: datetime) -> List[Obj]:
        cursor: Optional[Cursor] = None
        all_objects: List[Obj] = []
        while True:
            objects = get_objects(cursor)
            if not objects:
                return all_objects
            for obj in objects:
                date = get_date(obj)
                if date < start:
                    return all_objects
                if date < end:
                    all_objects.append(obj)
                cursor = get_cursor(obj)

    return func


get_all_comments = get_all(get_comments, get_comment_date, get_comment_cursor)


def get_merged_pr_count(start: datetime, end: datetime) -> int:
    query = """
        query($searchQuery:String!) {
            search(query:$searchQuery, type:ISSUE) {
                issueCount
            }
        }
    """
    variables = {
        "searchQuery": (
            f"is:pr "
            f"is:merged "
            f"org:urbanairship "
            f"author:{github_username} "
            f"merged:{start.isoformat()}..{end.isoformat()} "
        )
    }
    response = requests.post(
        url=GITHUB_GRAPHQL_URL,
        json={"query": query, "variables": variables},
        auth=github_auth(),
    )
    response.raise_for_status()
    data = response.json()
    return data["data"]["search"]["issueCount"]


def get_closed_ticket_count(start: datetime, end: datetime) -> int:
    response = requests.get(
        url=JIRA_SEARCH_URL,
        params={
            "jql": (
                f"assignee=currentUser()"
                f" AND resolved >= {start.date().isoformat()}"
                f" AND resolved <= {end.date().isoformat()}"
            )
        },
        auth=jira_auth(),
    )
    response.raise_for_status()
    data = response.json()
    return data["total"]


START = isoparse("2020-02-01T00:00:00Z")
END = isoparse("2021-02-01T00:00:00Z")

print(f"Calculating stats between {START.date()} and {END.date()}...")
print(f"PR comments left: {len(get_all_comments(START, END))}")
print(f"Merged PRs: {get_merged_pr_count(START, END)}")
print(f"Tickets closed: {get_closed_ticket_count(START, END)}")

