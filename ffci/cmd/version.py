import json

import click

from ffci.version import VERSION


@click.command()
@click.option("--output", "-o", default="json", type=click.Choice(["json", "text"]))
@click.pass_context
def version(ctx: click.Context, output: str) -> None:
    if output == "json":
        click.echo(json.dumps(VERSION.to_dict(), indent=2))
    else:
        click.echo(VERSION.text())
    ctx.exit()
