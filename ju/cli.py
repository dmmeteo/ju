import os
import sys
from functools import update_wrapper

import click
import configparser
from jira import JIRA, JIRAError

CONTEXT_SETTINGS = dict(auto_envvar_prefix='JU')


class Context(object):

    def __init__(self):
        self.verbose = False
        self.home = os.getcwd()
        self.config_path = os.path.expanduser('~/.jurc')
        self.aliases = {}
        self.jira_cfg = {}
        self.repositores = []
        self.read_config(self.config_path)

    def out(self, msg, **kwargs):
        """Out messages to stdout."""
        click.secho(msg, bold=True, err=True)

    def err(self, msg, **kwargs):
        """Out messages to stdout like error."""
        click.secho(msg, fg="red", err=False)

    def log(self, msg, *args):
        """Logs a message to stderr."""
        if args:
            msg %= args
        click.echo(msg, file=sys.stderr)

    def vlog(self, msg, *args):
        """Logs a message to stderr only if verbose is enabled."""
        if self.verbose:
            self.log(msg, *args)

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


pass_context = click.make_pass_decorator(Context, ensure=True)
cmd_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), 'commands'))


class ComplexCLI(click.MultiCommand):

    def list_commands(self, ctx):
        rv = []
        for filename in os.listdir(cmd_folder):
            if filename.endswith('.py') and filename.startswith('cmd_'):
                rv.append(filename[4:-3])
        rv.sort()
        return rv

    def get_command(self, ctx, name):
        try:
            if sys.version_info[0] == 2:
                name = name.encode('ascii', 'replace')
            mod = __import__(
                'ju.commands.cmd_%s'%name, None, None, ['cli']
            )
        except ImportError as e:
            print(e)
            return
        return mod.cli


# TODO fin refactor to pass_object
def pass_obj(f):
    @pass_context
    @click.pass_context
    def new_func(ctx, cfg, *args, **kwargs):
        for repo in cfg.repositores:
            try:
                ctx.invoke(f, ctx.obj, repo, *args, **kwargs)
            except Exception as e:
                click.echo(e)
                continue
    return update_wrapper(new_func, f)


@click.command(cls=ComplexCLI, context_settings=CONTEXT_SETTINGS)
@click.option(
    '--home',
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    help='Changes the folder to operate on.'
)
@click.option(
    '-v',
    '--verbose',
    is_flag=True,
    help='Enables verbose mode.'
)
@pass_context
def cli(ctx, verbose, home):
    """Application that help working in case multi repositories + Jira task tracker."""
    ctx.verbose = verbose
    if home is not None:
        ctx.home = home
