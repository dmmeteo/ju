import click
from ju.decorators import pass_config_loop


@click.command('diff', short_help='Shows file difference.')
@pass_config_loop
def cli(cfg, repo, *args, **kwargs):
    """Shows file difference in the current working directory."""
    colors = {
        '---': 'blue',
        '+++': 'yellow',
        '@@': 'magenta',
        '-': 'red',
        '+': 'green',
    }
    hg = cfg.hg_init(repo)
    cfg.out('Shows file difference via pager')

    branch = cfg.dec(hg.branch())
    lines = [click.style(
        '======> {}({}) <======\n'.format(repo.name, branch), fg='cyan'
    )]
    diff = cfg.dec(hg.diff())
    if diff:
        for row in diff.split('\n'):
            fg = 'white'
            for key, color in colors.items():
                if row.startswith(key):
                    fg = color
            lines.append(click.style(row, fg=fg))
        click.echo_via_pager('\n'.join(lines))
