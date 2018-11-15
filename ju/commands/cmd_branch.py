import click
from ju.decorators import pass_config_loop, jira_change_status
from hglib import error


@click.command('branch', short_help='Set/show branch.')
@click.argument('branch_name', required=False)
@click.option(
    '-C',
    '--clean',
    is_flag=True,
    help='discard uncommitted changes (no backup)'
)
# @jira_change_status('4', '951', '971')
@pass_config_loop
def cli(cfg, repo, *args, **kwargs):
    """Set or show the current branch name"""
    branch_name = cfg.enc(kwargs['branch_name'])
    hg = cfg.hg_init(repo, branch_name)
    if branch_name:
        hg.branch(name=branch_name)
        cfg.out('marked working directory as branch {}'.format(branch_name))
    else:
        current_branch = cfg.dec(hg.branch())
        cfg.out('Current branch: {}'.format(current_branch))
