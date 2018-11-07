from functools import update_wrapper

import click
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
