import click
from ju.decorators import pass_config


@click.command('config', short_help='Shows file changes.')
@click.option('-e', '--edit', is_flag=True, help='edit user config')
@pass_config
def cli(cfg, edit):
    """Show config file"""
    with open(cfg.config_path, 'r+') as f:
        text = f.read()
        if not edit:
            return click.echo_via_pager(text)
        new_text = click.edit(text)
        if new_text:
            with open(cfg.config_path, 'w') as wf:
                wf.write(new_text)