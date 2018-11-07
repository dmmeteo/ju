import os
import sys
from functools import update_wrapper

import click
import configparser
from jira import JIRA, JIRAError

CONTEXT_SETTINGS = dict(auto_envvar_prefix='JU')


class Context(object):
    """The config holds aliases, jira auth, and all reposirositores data."""

    def __init__(self):
        self.verbose = False
        # self.home = os.getcwd()
        self.config_path = os.path.expanduser('~/.jurc')
        self.aliases = {}
        self.jira_cfg = {}
        self.repositores = []
        self.read_config(self.config_path)
        self.jira_init()

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
            print(e)
            exit()

    def read_config(self, filename):
        if not os.path.isfile(filename):
            print('config file "~/.jurc" don\'t exists')
            exit()
        parser = configparser.ConfigParser()
        try:
            parser.read([filename])
            self.jira_cfg.update(parser.items('jira'))
            self.aliases.update(parser.items('aliases'))
            for k, v in parser.items():
                if k.startswith('repository:'):
                    self.repositores.append(v)
        except Exception as e:
            print(e)
            exit()


def pass_obj(f):
    @click.pass_context
    def new_func(ctx, *args, **kwargs):
        obj = ctx.ensure_object(Context)
        for repo in obj.repositores:
            try:
                ctx.invoke(f, ctx, *args, **kwargs)
            except Exception as e:
                click.echo(e)
                continue
    return update_wrapper(new_func, f)


pass_context = click.make_pass_decorator(Context, ensure=True)
cmd_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), 'commands'))


class ComplexCLI(click.MultiCommand):
    """This subclass of a group supports looking up aliases in a config
    file and with a bit of magic.
    """
    def list_commands(self, ctx):
        rv = []
        for filename in os.listdir(cmd_folder):
            if filename.endswith('.py') and filename.startswith('cmd_'):
                rv.append(filename[4:-3])
        rv.sort()
        return rv

    def import_command(self, ctx, name):
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

    def get_command(self, ctx, cmd_name):
        # Find the config object and ensure it's there.
        cfg = ctx.ensure_object(Context)

        # Lookup an explicit command aliase in the config
        if cmd_name in cfg.aliases:
            actual_cmd = cfg.aliases[cmd_name]
            return self.import_command(ctx, actual_cmd)

        # Alternative option: if we did not find an explicit alias we
        # allow automatic abbreviation of the command.  "status" for
        # instance will match "st". We only allow that however if
        # there is only one command.
        matches = [
            x for x in self.list_commands(ctx) if x.lower().startswith(cmd_name.lower())
        ]
        if not matches:
            return None
        elif len(matches) == 1:
            return self.import_command(ctx, matches[0])
        ctx.fail('Too many matches: %s' % ', '.join(sorted(matches)))


@click.command(cls=ComplexCLI, context_settings=CONTEXT_SETTINGS)
@click.option(
    '-v',
    '--verbose',
    is_flag=True,
    help='Enables verbose mode.'
)
@pass_obj
def cli(ctx, *args, **kwargs):
    """Application that help working in case multi repositories + Jira task tracker."""
    pass
