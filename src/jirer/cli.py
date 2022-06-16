"""Console script for jirer."""
import click

from src.jirer.__init__ import __version__

from src.jirer.jirer import Config, Jirer


@click.group()
@click.pass_context
@click.version_option(version=__version__)
def cli(ctx):
    ctx.jirer = Jirer(Config.load_or_create())

@cli.command("sprint")
@click.option("--assignee", "assignee", required=False, help="Filter the issues by assignee name.")
@click.option("--fetch", "fetch", default=False, is_flag=True, help="Force making a request, otherwise it uses a cache.")
@click.option("--json", "output_json", default=False, is_flag=True, help="Return raw json instead of displaying the table.")
@click.pass_context
def sprint(ctx, assignee, fetch, output_json):
    """Show the sprint.
    """
    ctx.parent.jirer.sprint(assignee, fetch, output_json)

@cli.command("transition")
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
    cli()  # pragma: no cover