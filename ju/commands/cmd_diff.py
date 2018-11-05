import click
from ju.cli import pass_context


@click.command('diff', short_help='Shows file difference.')
@pass_context
def cli(ctx):
    """Shows file difference in the current working directory."""
    ctx.log('Changed files: none')
    ctx.vlog('bla bla bla, debug info')