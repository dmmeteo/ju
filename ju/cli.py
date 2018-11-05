import os
import sys

import click
import configparser

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

    def log(self, msg, *args):
        """Logs a message to stderr."""
        if args:
            msg %= args
        click.echo(msg, file=sys.stderr)

    def vlog(self, msg, *args):
        """Logs a message to stderr only if verbose is enabled."""
        if self.verbose:
            self.log(msg, *args)

    def read_config(self, filename):
        """Init settings from config file"""
        parser = configparser.ConfigParser()
        parser.read([filename])
        try:
            # self.jira_cfg.update(parser.items('jira'))
            self.aliases.update(parser.items('aliases'))
            for k, v in parser.items():
                if k.startswith('repository:'):
                    self.repositores.append(v)
        except configparser.NoSectionError:
            pass


pass_context = click.make_pass_decorator(Context, ensure=True)
# TODO use environ in future
cmd_folder = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), 'commands')
)


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
    """A complex command line interface."""
    ctx.verbose = verbose
    if home is not None:
        ctx.home = home
