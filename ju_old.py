# from __future__ import unicode_literals

import os
from functools import partial, update_wrapper

import click
import configparser
import hglib
from jira import JIRA, JIRAError

# types
d = lambda s: s.decode('utf8')
out = partial(click.secho, bold=True, err=True)
err = partial(click.secho, fg="red", err=False)


def hg_init(repo, branch=None, quiet=False):
    def drop(*args, **kwargs):
        pass
    if quiet:
        out = err = drop
    try:
        hg = hglib.open(repo['path'])
        if not branch:
            branch = d(hg.branch())
        out('\n======> {}({}) <======'.format(repo.name, branch), fg='green')
        if hg.incoming():
            prefix = d(hg.paths()[b'default'])
            out('comparing with {}'.format(prefix))
            hg.pull()
        return hg
    except Exception as e:
        err('\n======> {} <======'.format(repo.name))
        click.echo(e)
        exit()


def status_colorize(files_list):
    change_color = {
        'M': 'blue',        # modified
        'A': 'green',       # added
        'R': 'yellow',      # removed
        'C': 'white',       # clean
        '!': 'cyan',        # missing (deleted by non-hg command, but still tracked)
        '?': 'red',         # not tracked
        'I': 'magenta',     # ignored
    }
    out('Changes not staged for commit:')
    for file in files_list:
        change, name = file
        change, name = d(change), d(name)
        out(
            click.style(
                '\t{} {}'.format(change, name),
                fg=change_color[change]
            ),
            bold=False
        )


class Config(object):
    """The config holds aliases, jira auth, and all reposirositores data."""

    def __init__(self):
        self.config_path = os.path.expanduser('~/.jurc')
        self.aliases = {}
        self.jira_cfg = {}
        self.repositores = []
        self.read_config(self.config_path)
        self.jira_init()

    def jira_init(self):
        try:
            self.jira = JIRA(
                server=self.jira_cfg['server'],
                basic_auth=(
                    self.jira_cfg['username'],
                    self.jira_cfg['password']
                ),
            )
        except JIRAError as e:
            click.echo(e)
            exit(-1)

    def read_config(self, filename):
        parser = configparser.ConfigParser()
        parser.read([filename])
        try:
            self.jira_cfg.update(parser.items('jira'))
            self.aliases.update(parser.items('aliases'))
            for k, v in parser.items():
                if k.startswith('repository:'):
                    self.repositores.append(v)
        except configparser.NoSectionError:
            pass


pass_config = click.make_pass_decorator(Config, ensure=True)


# TODO fin refactor to pass_object
def pass_obj(f):
    @pass_config
    @click.pass_context
    def new_func(ctx, cfg, *args, **kwargs):
        for repo in cfg.repositores:
            try:
                ctx.invoke(f, ctx, cfg, repo, *args, **kwargs)
            except Exception as e:
                click.echo(e)
                continue
    return update_wrapper(new_func, f)


class AliasedGroup(click.Group):
    """This subclass of a group supports looking up aliases in a config
    file and with a bit of magic.
    """

    def get_command(self, ctx, cmd_name):
        # Step one: bulitin commands as normal
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv

        # Step two: find the config object and ensure it's there.  This
        # will create the config object is missing.
        cfg = ctx.ensure_object(Config)

        # Step three: lookup an explicit command aliase in the config
        if cmd_name in cfg.aliases:
            actual_cmd = cfg.aliases[cmd_name]
            return click.Group.get_command(self, ctx, actual_cmd)

        # Alternative option: if we did not find an explicit alias we
        # allow automatic abbreviation of the command.  "status" for
        # instance will match "st".  We only allow that however if
        # there is only one command.
        matches = [
            x for x in self.list_commands(ctx) if x.lower().startswith(cmd_name.lower())
        ]
        if not matches:
            return None
        elif len(matches) == 1:
            return click.Group.get_command(self, ctx, matches[0])
        ctx.fail('Too many matches: %s' % ', '.join(sorted(matches)))


@click.command(cls=AliasedGroup)
def cli():
    """Application that help working in case multi repositories + Jira task tracker."""


@cli.command()
@click.option('-e', '--edit', is_flag=True, help='edit user config')
@pass_config
def config(cfg, edit):
    """Show config file"""
    with open(cfg.config_path, 'r+') as f:
        text = f.read()
        if not edit:
            return click.echo_via_pager(text)
        new_text = click.edit(text)
        if new_text:
            with open(cfg.config_path, 'w') as wf:
                wf.write(new_text)


@cli.command()
@pass_obj
def status(ctx, cfg, repo, **options):
    """Shows the status."""
    # TODO options like --modified, --added, etc.
    hg = hg_init(repo)
    untracked = hg.status()
    if untracked:
        status_colorize(untracked)
    else:
        branch = d(hg.branch())
        out('On branch {}'.format(branch))
        out('nothing to commit, working tree clean')


@cli.command()
@pass_obj
def diff(ctx, cfg, repo, **options):
    """diff repository (or selected files)"""
    colors = {
        '---': 'blue',
        '+++': 'yellow',
        '@@': 'magenta',
        '-': 'red',
        '+': 'green',
    }
    hg = hg_init(repo)
    branch = d(hg.branch())
    lines = [click.style('\n======> {}({}) <======\n\n'.format(repo.name, branch), fg='cyan')]
    diff = d(hg.diff())
    if diff:
        for row in diff.split('\n'):
            fg = 'white'
            for key, color in colors.items():
                if row.startswith(key):
                    fg = color
            lines.append(click.style(row, fg=fg))
        click.echo_via_pager('\n'.join(lines))


@cli.command()
@click.argument('branch_name', required=False)
@click.option(
    '-C',
    '--clean',
    is_flag=True,
    help='discard uncommitted changes (no backup)'
)
@pass_obj
def branch(ctx, cfg, repo, branch_name, clean):
    """set or show the current branch name"""
    hg = hg_init(repo, branch_name)
    current_branch = d(hg.branch())
    if branch_name:
        try:
            hg.branch(name=branch_name.encode('ascii'))
            out('marked working directory as branch {}'.format(branch_name))
        except hglib.error.CommandError as e:
            err(e)
    else:
        out('BRANCH: {}'.format(current_branch))


@cli.command()
@click.argument('branch_name')
@click.option(
    '-C',
    '--clean',
    is_flag=True,
    help='discard uncommitted changes (no backup)'
)
@pass_obj
def update(ctx, cfg, repo, branch_name, clean, quiet=False):
    """update working directory (or switch revisions)"""
    hg = hg_init(repo, branch_name, quiet)
    untracked = hg.status()
    if untracked:
        status_colorize(untracked)
        if click.confirm('Do you want to commit and push all files?', abort=False):
            message = click.prompt('Enter commit message')
            ctx.invoke(commit, message=message)
            ctx.invoke(push, branch_name=branch_name)
            # cfg.hg.push(dest=cfg.repository['url'], branch=branch, newbranch=True)

    u, m, r, un = hg.update(branch_name, clean=clean)
    out('{} files updated, {} files merged, {} files removed, {} files unresolved'.format(u, m, r, un))
    out('marked working directory as branch {}'.format(branch_name))


@cli.command()
@click.argument('branch_name')
@pass_obj
def start(ctx, cfg, repo, branch_name):
    """start progress the ticket by branch name"""
    # run update default
    default_branch = repo.get('default_branch', 'default')
    ctx.invoke(update, branch_name=default_branch, clean=True, quiet=True)

    # # run jira
    # jira = cfg.jira
    # issue = jira.issue(branch)
    # username = cfg.jira_cfg['username']
    # if jira.user(username) != issue.fields.assignee:
    #     jira.assign_issue(issue, username)
    # for status in jira.transitions(issue):
    #     if status['id'] in ['4', '951', '971']:
    #         jira.transition_issue(issue, transition=status['id'])
    #         out(status['name'])

    # run branch
    ctx.invoke(branch, branch_name=branch_name, clean=True)


@cli.command()
@click.argument('branch_name', required=False)
@pass_obj
def push(ctx, cfg, repo, branch_name):
    """push changes to the specified destination"""
    hg = hg_init(repo)
    untracked = hg.status()
    if untracked:
        status_colorize(untracked)
        if click.confirm(
            'Do you want to added and commit untracked files?', default=True
        ):
            message = click.prompt('Enter commit message')
            hg.commit(message=message, addremove=True)
    try:
        if branch_name:
            branch_name = branch_name.encode('ascii')
        if hg.push(dest=repo['http_basic'].encode('ascii'), branch=branch_name, newbranch=True):
            out('push was successful')
        else:
            out('nothing to push')
    except hglib.error.CommandError as e:
        click.echo(e)


@cli.command()
@pass_obj
def clone(ctx, cfg, repo):
    """make a copy of an existing repository"""
    hglib.clone(source=repo['http_basic'], dest=repo['path'])
    hg_init(repo)
    out('clone was successful')


@cli.command()
@click.option(
    '--message',
    '-m',
    prompt='Enter commit message',
    help='The commit message. If provided multiple times each argument gets converted into a new line.',
)
@pass_obj
@click.option('--close-branch', is_flag=True, help='mark a branch head as closed')
def commit(ctx, cfg, repo, message, close_branch):
    """commit the specified files or all outstanding changes"""
    hg = hg_init(repo)
    current_branch = d(hg.branch())
    # TODO not tracked
    addremove = False
    untracked = hg.status()
    b_message = '{} {}'.format(current_branch, message)
    if untracked:
        status_colorize(untracked)
        if click.confirm('Do you want to added untracked files?'):
            addremove = True
    hg.commit(message=b_message, addremove=addremove, closebranch=close_branch)
    out('commit was successful')


@cli.command()
@click.argument('branch', required=False)
@click.confirmation_option()
@pass_obj
def done(ctx, cfg, repo, branch):
    '''Checking fo uncommited code, then changing status in jira to "waiting for ci"'''
    hg = hg_init(repo)
    branch = branch if branch else d(hg.branch())
    untracked = hg.status()
    if untracked:
        status_colorize(untracked)
        if click.confirm('Do you want to commit and push all files?', abort=True):
            message = click.prompt('Enter commit message')
            ctx.invoke(commit, ctx, cfg, repo, message=message)
            ctx.invoke(push, ctx, cfg, repo, branch=branch)

    # jira working
    jira = cfg.jira
    issue = jira.issue(branch)
    if str(jira.user(cfg.jira_cfg['username'])) != str(issue.fields.assignee):
        if click.confirm(
            'Issue is already assigned to another user. Do you want to continue?',
            abort=True,
        ):
            pass
    for status in jira.transitions(issue):
        if status['id'] == '861':
            jira.transition_issue(issue, transition='861')
            out(status['name'])


@cli.command()
@click.argument('branch')
@pass_config
@click.pass_context
def merge(ctx, cfg, branch):
    """(comming soon)merge another revision into working directory"""
    pass


@cli.command()
@click.option(
    '-c',
    '--closed',
    is_flag=True,
    help='show normal and closed branches'
)
@pass_config
def branches(cfg, closed):
    """(comming soon)list repository named branches"""
    # call('hg branches', shell=True)
    pass
