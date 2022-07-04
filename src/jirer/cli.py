"""Console script for jirer."""
import click

from jirer.__init__ import __version__

from jirer.jirer import Config, Jirer


@click.group()
@click.pass_context
@click.version_option(version=__version__)
def main(ctx):
    ctx.jirer = Jirer(Config.load_or_create())

@main.command("sprint")
@click.option("--assignee", "assignee", required=False, help="Filter the issues by assignee name.")
@click.option("--select-assignee", "select_assignee", is_flag=True, help="Select and assignee, needs fzf (brew/apt install fzf).")
@click.option("--show-all", "show_all", is_flag=True, help="Show the issues for all the assignees.")
@click.option("--fetch", "fetch", default=False, is_flag=True, help="Force making a request, otherwise it uses a cache.")
@click.option("--json", "output_json", default=False, is_flag=True, help="Return raw json instead of displaying the table.")
@click.option("--pager", "with_pager", default=False, is_flag=True, help="User pager.")
@click.pass_context
def sprint(ctx, assignee, select_assignee, show_all, fetch, output_json, with_pager):
    """Show the sprint.
    """
    ctx.parent.jirer.sprint(assignee, select_assignee, show_all, fetch, output_json, with_pager)

@main.command("transition")
@click.argument("issue")
@click.argument("name", type=click.Choice(Jirer.TRANSITIONS.keys()), required=False)
@click.pass_context
def transition(ctx, issue, name=None):
    """Transition issue.

    ISSUE can be for example "WDE-123".
    """
    if not name:
        name = click.prompt('Select transition', type=click.Choice(Jirer.TRANSITIONS.keys()))
    ctx.parent.jirer.transition(issue, name)


if __name__ == '__main__':
    main()  # pragma: no cover