import os
import sys

import click
from ju.config import Config
from ju.decorators import pass_config_loop

CONTEXT_SETTINGS = dict(auto_envvar_prefix='JU')
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
        cfg = ctx.ensure_object(Config)

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
@pass_config_loop
def cli(ctx, *args, **kwargs):
    """Application that help working in case multi repositories + Jira task tracker."""
    pass
