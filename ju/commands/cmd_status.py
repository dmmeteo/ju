import click
from ju.cli import pass_context


@click.command('status', short_help='Shows file changes.')
@pass_context
def cli(ctx):
    """Shows file changes in the current working directory."""
    ctx.out('Changed files: none')
    ctx.vlog('bla bla bla, debug info')