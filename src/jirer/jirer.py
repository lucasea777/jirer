# import sys
# # from IPython.core import ultratb
# # sys.excepthook = ultratb.FormattedTB(mode='Verbose',
# #      color_scheme='Linux', call_pdb=1)
# import os
# os.environ['PYTHONBREAKPOINT'] = 'ipdb.set_trace'
# # import debugpy

# # debugpy.listen(5678)
# # print("Waiting for debugger attach")
# # debugpy.wait_for_client()

from dataclasses import dataclass
from dataclasses import asdict
import subprocess
import sys

from pathlib import Path
import json
import requests
from requests.auth import HTTPBasicAuth
from rich.console import Console
from rich.table import Table

CONFIG_PATH = Path("~/.jirer-console-config").expanduser()
AUTH_PATH = CONFIG_PATH / "atlassian_api_key.json"
CACHE = CONFIG_PATH / "raw.json"


def deep_get(dictionary, key):
    """
    >>> deep_get({"a": {"b": 3}}, "a")
    {"a": {"b": 3}}
    >>> deep_get({"a": {"b": 3}}, "a.b")
    3
    >>> deep_get({"a": {"b": 3}}, "c")
    >>> deep_get({"a": {"b": 3}}, "a.c")
    >>> deep_get({"a": {"b": {"c": 4}}}, "a.b")
    {"c": 4}
    >>> deep_get({"a": {"b": {"c": 4}}}, "a.b.c.s")
    """
    keylist = key.split(".")[::-1]
    def _deep_get(dictionary, keylist):
        if keylist:
            _next = keylist.pop()
            item = dictionary.get(_next, None)
            if keylist and type(item) == dict:
                return _deep_get(item, keylist)
            if not keylist:                    
                return item
    return _deep_get(dictionary, keylist) or ""


def get_points(raw_issue):
    """
    The points field is custom and depends on the jirer configuration, to find it you can call '$ jirer.py sprint --fetch --json'
    """
    if deep_get(raw_issue, "fields.customfield_10008"):
        return str(int(deep_get(raw_issue, "fields.customfield_10008")))
    else:
        return ""

def render(assignee, data, domain, use_pager):
    table = Table(title=assignee, show_lines=True)

    table.add_column("Name", justify="right", style="cyan", no_wrap=True)
    table.add_column("Status", justify="right", style="cyan", no_wrap=True)
    table.add_column("Id", style="magenta")
    table.add_column("Points", justify="right", style="green")
    table.add_column("Description", style="magenta", max_width=80)

    for row in data:
        table.add_row(
            row["name"],
            row["status"], 
            row["id"], 
            row["points"],
            "[bold][underline]" + row.get("summary", "") + "[/bold][/underline]\n" 
            + (row["description"] or "")
            + "\n" + f"https://{domain}/browse/" + row["id"])
    console = Console()
    if use_pager:
        with console.pager(styles=True):
            console.print(table)
    else:
        console.print(table)

@dataclass
class Config:
    key: str = None
    user: str = None
    domain: str = None
    default_assignee: str = None

    @classmethod
    def load_or_create(cls) -> None:
        if not CONFIG_PATH.exists():
            print("Hi! 👋, please go to https://id.atlassian.com/manage-profile/security/api-tokens and generate a 🔑 (dont loose it!)")
            config = cls(
                domain=input("domain (usually thecompany.atlassian.net): "),
                user=input("user (looks like my.user@domain.com): "),
                key=input("key: "),
                default_assignee=input("default_assignee (used to filter, e.g. 'Lucas'): ")
            )
            CONFIG_PATH.mkdir()
            AUTH_PATH.write_text(json.dumps(asdict(config)))
            print(f"Generated {AUTH_PATH}")
            return config
        return cls(**json.loads(AUTH_PATH.read_text()))
        

# JQL = """
# issuetype != Epic AND Sprint in openSprints() AND assignee = '{assignee}@domain.com'
# """.strip()

class Jirer:
    RAW_ENDPOINT = "https://{domain}/rest/api/2"
    JQL = """
        issuetype != Epic AND Sprint in openSprints()
        """.strip()

    TRANSITIONS = {
        "todo": "Por hacer",
        "progress": "En curso",
        "done": "Listo",
        "cr": "Code Review",
        "testing": "Testing"
    }

    def __init__(self, config: Config) -> None:
        self.config = config

    @property
    def endpoint(self):
        return self.RAW_ENDPOINT.format(domain=self.config.domain)

    @property
    def http_auth(self):
        return HTTPBasicAuth(self.config.user, self.config.key)

    def get_raw(self):
        return requests.get(
            f"{self.endpoint}/search",
            auth=self.http_auth,
            params={
                "jql": self.JQL
            }
        ).json()

    @staticmethod
    def extract(raw):
        records = [{
            "name": deep_get(r, "fields.assignee.displayName"),
            "email": deep_get(r, "fields.assignee.emailAddress"),
            "id": r["key"],
            "description": deep_get(r, "fields.description"),
            "status": deep_get(r, "fields.status.name"),
            "summary": deep_get(r, "fields.summary"),
            "type": deep_get(r, "fields.issuetype.name"),
            "points": get_points(r)
        } for r in raw["issues"]]
        return records

    @staticmethod
    def get_assignees(records):
        return [r["name"] for r in records]

    @staticmethod
    def filter_assignee(records, assignee):
        return [
            {k: v for k, v in r.items()} 
            for r in records if assignee.lower() in (r["name"] or "").lower()]

    def get_transitions(self, issue):
        raws = requests.get(
            f"{self.endpoint}/issue/{issue}/transitions",
            auth=self.http_auth
            ).json()
        return {raw["name"]: raw["id"] for raw in raws["transitions"]}

    def perform_transition(self, issue, tid):
        r = requests.post(
            f"{self.endpoint}/issue/{issue}/transitions",
            auth=self.http_auth,
            json={
                "transition": {
                    "id": tid
                }
            })
        if r.status_code != 204:
            raise Exception(f"not {r.status_code}!=204 {r.text}")

    def sprint(self, assignee, select_assignee, show_all, fetch, output_json, use_pager):
        # import IPython; IPython.embed(colors="neutral")
        if fetch or not Path(CACHE).exists():
            raw = self.get_raw()
            Path(CACHE).write_text(json.dumps(raw))
        else:
            raw = json.loads(Path(CACHE).read_text())
        if output_json:
            print(json.dumps(raw))
            sys.exit()
        data = self.extract(raw)
        if select_assignee:
            candidates = self.get_assignees(data)
            assignee = self.ask_choose_assignee(candidates)
        if not show_all:
            assignee = assignee or self.config.default_assignee
        data = self.filter_assignee(data, assignee or "")
        render(assignee, data, self.config.domain, use_pager)

    def ask_choose_assignee(self, candidates):
        candidates = list(set(candidates))
        try:
            assignee = subprocess.run(
                    "fzf",
                    input=bytes("\n".join(candidates), "utf8"), 
                    stdout=subprocess.PIPE
                ).stdout.decode().strip()
        except FileNotFoundError:
            raise Exception(
                "To choose an assignee (as opposed to --show-all or passing one with --assignee) you need fzf.\n"
                "Install it like so: \"brew/apt install fzf\"."
            )
        
        return assignee


    def transition(self, issue, name=None):
        tr = self.get_transitions(issue)
        self.perform_transition(issue, tr[self.TRANSITIONS[name]])
