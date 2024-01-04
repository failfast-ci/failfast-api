#!/usr/bin/env python3
import asyncio
import functools
import click
import json

from ffci.config import GConfig
from ffci.client import GGithubClient


def make_sync(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))
    return wrapper

@click.group()
@click.pass_context
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    default=None,
    help="Configuration file in YAML format.",
    show_default=True,
)
def github(ctx: click.Context, config: str) -> None:
    ctx.ensure_object(dict)
    ctx.obj['config'] = GConfig(config)

@github.command()
@click.option("--output", "-o", default="json", type=click.Choice(["json", "text"]))
@click.pass_context
@make_sync
async def token(ctx: click.Context, output: str) -> None:
    client = GGithubClient()
    try:
        token = await client.get_token()
        if output == "json":
            click.echo(json.dumps({"token": token}, indent=2))
        else:
            click.echo(token)
    finally:
        ctx.exit()

@github.command()
@click.option("--output", "-o", default="json", type=click.Choice(["json", "text"]))
@click.pass_context
@make_sync
async def jwt(ctx: click.Context, output: str) -> None:
    client = GGithubClient()
    try:
      token = client.jwt_token()
      if output == "json":
          click.echo(json.dumps({"jwt_token": token}, indent=2))
      else:
          click.echo(token)
    finally:
        ctx.exit()

@github.command()
@click.option("--output", "-o", default="json", type=click.Choice(["json", "text"]))
@click.pass_context
@make_sync
async def headers(ctx: click.Context, output: str) -> None:
    client = GGithubClient()
    try:
        headers = await client.headers()
        if output == "json":
            click.echo(json.dumps(headers, indent=2))
        else:
            click.echo(headers)
        ctx.exit()
    finally:
        await client.close()

@github.command()
@click.option("--output", "-o", default="json", type=click.Choice(["json", "text"]))
@click.pass_context
@make_sync
async def get_ci_file(ctx: click.Context, output: str) -> None:
    client = GGithubClient()
    try:
        resp = await client.get_ci_file("failfast-ci/failfast-api", "main")
        if output == "json":
            click.echo(json.dumps({"content": resp}, indent=2))
        else:
            click.echo(resp)
        ctx.exit()
    finally:
        await client.close()
