from functools import update_wrapper

import click
from jira import JIRA, JIRAError
from ju.cli import Config

pass_config = click.make_pass_decorator(Config, ensure=True)


def pass_config_loop(f):
    @click.pass_context
    def new_func(ctx, *args, **kwargs):
        obj = ctx.ensure_object(Config)
        for repo in obj.repositores:
            try:
                ctx.invoke(f, obj, repo, *args, **kwargs)
            except Exception as e:
                click.echo(e)
                continue
    return update_wrapper(new_func, f)


def jira_change_status(*args, **kwargs):
    def pass_func(f):
        @click.pass_context
        def new_func(ctx, *args, **kwargs):
            obj = ctx.ensure_object(Config)
            cfg = obj.jira_cfg
            try:
                jira = JIRA(
                    server=cfg['server'],
                    basic_auth=(
                        cfg['username'],
                        cfg['password']
                    ),
                )
                f(*args, **kwargs)
                issue = jira.issue(kwargs['branch_name'])
            # TODO JIRAError's
            except Exception as e:
                click.echo(e)
            else:
                username = cfg['username']
                if jira.user(username) != issue.fields.assignee:
                    jira.assign_issue(issue, username)
                for status in jira.transitions(issue):
                    if status['id'] in args:
                        # jira.transition_issue(issue, transition=status['id'])
                        obj.out(status['name'])
        return new_func
    return pass_func
