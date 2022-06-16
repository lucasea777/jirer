from dataclasses import dataclass
from dataclasses import asdict
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

def get_points(raw_issue):
    """
    The points field is custom and depends on the jirer configuration, to find it you can call '$ jirer.py sprint --fetch --json'
    """
    if raw_issue["fields"].get("customfield_10008"):
        return str(int(raw_issue["fields"]["customfield_10008"]))
    else:
        return "customfield_10008 not available"

def render(assignee, data, domain):
    table = Table(title=assignee, show_lines=True)

    table.add_column("Status", justify="right", style="cyan", no_wrap=True)
    table.add_column("Id", style="magenta")
    table.add_column("Points", justify="right", style="green")
    table.add_column("Description", style="magenta", max_width=80)

    for row in data:
        table.add_row(
            row["status"], 
            row["id"], 
            row["points"],
            "[bold][underline]" + row.get("summary", "") + "[/bold][/underline]\n" 
            + (row["description"] or "")
            + "\n" + f"https://{domain}/browse/" + row["id"])
    console = Console()
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
    def extract(raw, assignee=None):
        records = [{
            "name": r["fields"]["assignee"]["displayName"],
            "email": r["fields"]["assignee"].get("emailAddress"),
            "id": r["key"],
            "description": r["fields"]["description"],
            "status": r["fields"]["status"]["name"],
            "summary": r["fields"]["summary"],
            "type": r["fields"]["issuetype"]["name"],
            "points": get_points(r)
        } for r in raw["issues"]]
        if not assignee:
            return records
        return [
            {k: v for k, v in r.items() if k not in {"name", "email"}} 
            for r in records if assignee.lower() in r["name"].lower()]

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

    def sprint(self, assignee, fetch, output_json):
        assignee = assignee or self.config.default_assignee
        # import IPython; IPython.embed(colors="neutral")
        if fetch or not Path(CACHE).exists():
            raw = self.get_raw()
            Path(CACHE).write_text(json.dumps(raw))
        else:
            raw = json.loads(Path(CACHE).read_text())
        if output_json:
            print(json.dumps(raw))
            sys.exit()
        data = self.extract(raw, assignee=assignee)
        render(assignee, data, self.config.domain)


    def transition(self, issue, name=None):
        tr = self.get_transitions(issue)
        self.perform_transition(issue, tr[self.TRANSITIONS[name]])
