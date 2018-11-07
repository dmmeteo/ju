import click
from ju.cli import pass_context, pass_obj


@click.command('status', short_help='Shows file changes.')
@pass_obj
def cli(ctx, *args, **kwargs):
    """Shows file changes in the current working directory."""
    obj = ctx.obj
    obj.out('Changed files: none')
    obj.vlog('bla bla bla, debug info')