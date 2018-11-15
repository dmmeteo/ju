import os
import sys

import click
import configparser
import hglib


class Config(object):
    """The config holds aliases, jira auth, and all reposirositores data."""

    def __init__(self):
        self.verbose = False
        self.config_path = os.path.expanduser('~/.jurc')
        self.aliases = {}
        self.jira_cfg = {}
        self.repositores = []
        self.read_config(self.config_path)

    def read_config(self, filename):
        if not os.path.isfile(filename):
            self.err('Config file "~/.jurc" don\'t exists')
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
            self.err(e)
            exit()

    def hg_init(self, repo, branch=None, quiet=False):
        dec = self.dec
        out = self.vlog if quiet else self.out
        err = self.vlog if quiet else self.err

        try:
            hg = hglib.open(repo['path'])
            if not branch:
                branch = dec(hg.branch())
            if hg.incoming():
                prefix = dec(hg.paths()[b'default'])
                out('comparing with {}'.format(prefix))
                hg.pull()
        except hglib.error.ServerError as e:
            err('\n======> {} <======'.format(repo.name))
            print(type(e))
            out(e)
        else:
            out('\n======> {}({}) <======'.format(repo.name, branch), fg='green')
            return hg

    def out(self, msg, **kwargs):
        """Out messages to stdout."""
        options = dict(bold=True, err=True)
        options.update(**kwargs)
        click.secho(msg, **options)

    def err(self, msg, **kwargs):
        """Out messages to stdout like error."""
        options = dict(fg="red", err=True)
        options.update(**kwargs)
        click.secho(msg, **options)

    def dec(self, string):
        """Converts a value into a valid string."""
        return click.utils.make_str(string)

    def enc(self, string):
        """Converts a value into a valid bytes."""
        if isinstance(string, str):
            return string.encode('utf-8', 'replace')
        return string

    def status_colorize(self, lines_list):
        change_color = {
            'M': 'blue',        # modified
            'A': 'green',       # added
            'R': 'yellow',      # removed
            'C': 'white',       # clean
            '!': 'cyan',        # missing (deleted by non-hg command, but still tracked)
            '?': 'red',         # not tracked
            'I': 'magenta',     # ignored
        }
        self.out('Changes not staged for commit:')
        for line in lines_list:
            change, name = line
            change, name = self.dec(change), self.dec(name)
            self.out(
                click.style(
                    '\t{} {}'.format(change, name),
                    fg=change_color[change]
                ),
                bold=False
            )

    def log(self, msg, *args, **kwargs):
        """Logs a message to stderr."""
        if args:
            msg %= args  # TODO something
        click.echo(msg, file=sys.stderr)

    def vlog(self, msg, *args, **kwargs):
        """Logs a message to stderr only if verbose is enabled."""
        if self.verbose:
            self.log(msg, *args, **kwargs)
