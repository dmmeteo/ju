import click
from ju.decorators import pass_config_loop


@click.command('status', short_help='Shows file changes.')
@pass_config_loop
def cli(cfg, repo, *args, **kwargs):
    """Shows file changes in the current working directory."""
    # TODO options like --modified, --added, etc.
    hg = cfg.hg_init(repo)
    changes = hg.status()
    if changes:
        cfg.status_colorize(changes)
    else:
        branch = cfg.dec(hg.branch())
        cfg.out('On branch {}'.format(branch))
        cfg.out('nothing to commit, working tree clean')
