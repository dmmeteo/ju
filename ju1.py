import os
import click
import hglib
from jira import JIRA, JIRAError
from subprocess import call
import configparser
from functools import partial


# types
d = lambda s: s.decode('utf8')
out = partial(click.secho, bold=True, err=True)
err = partial(click.secho, fg="red", err=False)

def hg_init(repo):
    try:
        hg = hglib.open(repo['path'])
        branch = d(hg.branch())
        out('\n======> {}({}) <======'.format( repo.name, branch ), fg='green')
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
        out(click.style(
            '\t{} {}'.format( d(change), d(name) ),
            fg=change_color[d(change)]),
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
    """Application that help working in case jira+mercurial."""


@cli.command()
@click.option('-e', '--edit', is_flag=True, help='edit user config')
@pass_config
def config(cfg, edit):
        with open(cfg.config_path, 'r+') as f:
            text = f.read()
            if not edit:
                return click.echo_via_pager(text)
            new_text = click.edit(text)
            if new_text:
                with open(cfg.config_path, 'w') as wf:
                    wf.write(new_text)


@cli.command()
@pass_config
def status(cfg, **options):
    """Shows the status."""
    # TODO options like --modified, --added, etc.
    for repo in cfg.repositores:
        try:
            hg = hg_init(repo)
            untracked = hg.status()
            if untracked:
                status_colorize(untracked)
            else:
                out('On branch {}'.format( d(hg.branch()) ))
                out('nothing to commit, working tree clean')
        except Exception as e:
            clicl.echo(e)
            continue


@cli.command()
@pass_config
def diff(cfg, **options):
    """diff repository (or selected files)"""
    colors = {
        '---': 'blue',
        '+++': 'yellow',
        '@@': 'magenta',
        '-': 'red',
        '+': 'green',
    }
    for repo in cfg.repositores:
        try:
            hg = hg_init(repo)
            branch = d(hg.branch())
            lines = [click.style('\n======> {}({}) <======\n\n'.format( repo.name, branch ), fg='cyan')]
            diff = d(hg.diff())
            if diff:
                for row in diff.split('\n'):
                    fg = 'white'
                    for key, color in colors.items():
                        if row.startswith(key):
                            fg = color
                    lines.append(click.style(row, fg=fg))
                click.echo_via_pager('\n'.join(lines))
        except Exception as e:
            clicl.echo(e)
            continue


@cli.command()
@click.argument('branch', required=False)
@click.option('-C', '--clean', is_flag=True, help='discard uncommitted changes (no backup)')
@pass_config
def branch(cfg, branch, clean):
    """set or show the current branch name"""
    for repo in cfg.repositores:
        try:
            hg = hg_init(repo)
            jira = cfg.jira
            current_branch = d(hg.branch())
            default_branch = repo.get('default_branch', 'default')
            if branch:
                # jira working
                issue = jira.issue(branch)
                username = cfg.jira_cfg['username']
                if jira.user(username) != issue.fields.assignee:
                    jira.assign_issue(issue, username)
                for status in jira.transitions(issue):
                    if status['id'] == '4':
                        jira.transition_issue(issue, transition='4')
                        out(status['name'])

                # hg working
                if hg.incoming():
                    prefix = d(hg.paths()[b'default'])
                    out('comparing with {}'.format(prefix))
                    hg.pull()
                u, m, r, un = hg.update(default_branch, clean=clean)
                try:
                    hg.branch(name=branch.encode('ascii'))
                except hglib.error.CommandError as e:
                    hg.update(branch)
                out('{} files updated, {} files merged, {} files removed, {} files unresolved'.format(u, m, r, un))
                out('marked working directory as branch {}'.format(branch))
            else:
                out('BRANCH: {}'.format(current_branch))
        except Exception as e:
            click.echo(e)
            continue


@cli.command()
@click.argument('branch', required=False)
@pass_config
def push(cfg, branch):
    """push changes to the specified destination"""
    for repo in cfg.repositores:
        try:
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
                if branch:
                    branch = branch.encode('ascii')
                if hg.push(dest=repo['http_basic'].encode('ascii'), branch=branch, newbranch=True):
                    out('push was successful')
                else:
                    out('nothing to push')
            except hglib.error.CommandError as e:
                click.echo(e)
        except Exception as e:
            click.echo(e)
            continue


@cli.command()
@pass_config
def clone(cfg):
    """make a copy of an existing repository"""
    for repo in cfg.repositores:
        try:
            hglib.clone(source=repo['http_basic'], dest=repo['path'])
            hg = hg_init(repo)
            out('clone was successful')
        except Exception as e:
            click.echo(e)
            continue


@cli.command()
@click.option(
    '--message',
    '-m',
    prompt='Enter commit message',
    help='The commit message. If provided multiple times each argument gets converted into a new line.',
)
@pass_config
@click.option('--close-branch', is_flag=True, help='mark a branch head as closed')
def commit(cfg, message, close_branch):
    """commit the specified files or all outstanding changes"""
    for repo in cfg.repositores:
        try:
            hg = hg_init(repo)
            current_branch = d(hg.branch())
            addremove = False
            untracked = hg.status()
            b_message = '{} {}'.format(current_branch, message)
            if untracked:
                status_colorize(untracked)
                if click.confirm('Do you want to added untracked files?'):
                    addremove = True
            hg.commit(message=message, addremove=addremove, closebranch=close_branch)
            out('commit was successful')
        except Exception as e:
            click.echo(e)
            continue


@cli.command()
@click.argument('branch', required=False)
@click.confirmation_option()
@pass_config
@click.pass_context
def done(ctx, cfg, branch):
    '''Checking fo uncommited code, then changing status in jira to "waiting for ci"'''
    for repo in cfg.repositores:
        try:
            hg = hg_init(repo)
            branch = branch.encode('ascii') if branch else hg.branch()
            untracked = hg.status()
            if untracked:
                status_colorize(untracked)
                if click.confirm('Do you want to commit and push all files?', abort=True):
                    message = click.prompt('Enter commit message')
                    ctx.invoke(commit, message=message)
                    cfg.hg.push(dest=cfg.repository['url'], branch=branch, newbranch=True)
            
            #jira working
            jira = cfg.jira
            issue = jira.issue(branch)
            if str(jira.user(cfg.jira_cfg['login'])) != str(issue.fields.assignee):
                if click.confirm(
                    'Issue is already assigned to another user. Do you want to continue?',
                    abort=True,
                ):
                    pass
            for status in jira.transitions(issue):
                if status['id'] == '861':
                    jira.transition_issue(issue, transition='861')
                    out(status['name'])

        except Exception as e:
            click.echo(e)
            continue


@cli.command()
@click.argument('branch')
@click.option('-C', '--clean', is_flag=True, help='discard uncommitted changes (no backup)')
@pass_config
@click.pass_context
def update(ctx, cfg, branch, clean):
    """update working directory (or switch revisions)"""
    for repo in cfg.repositores:
        try:
            hg = hg_init(repo)
            untracked = hg.status()
            if untracked:
                status_colorize(untracked)
                if click.confirm('Do you want to commit and push all files?', abort=False):
                    message = click.prompt('Enter commit message')
                    ctx.invoke(commit, message=message)
                    cfg.hg.push(dest=cfg.repository['url'], branch=branch, newbranch=True)

            if hg.incoming():
                prefix = d(hg.paths()[b'default'])
                out('comparing with {}'.format(prefix))
                hg.pull()
            u, m, r, un = hg.update(branch, clean=clean)
            out('{} files updated, {} files merged, {} files removed, {} files unresolved'.format(u, m, r, un))
            out('marked working directory as branch {}'.format(branch))

        except Exception as e:
            click.echo(e)
            continue


@cli.command()
@click.option('-c', '--closed', is_flag=True, help='show normal and closed branches')
@pass_config
def branches(cfg, closed):
    """list repository named branches"""
    # call('hg branches', shell=True)
    pass



