#!/usr/bin/env python3
import click
from temporalloop.main import main as looper_main

from .default_config import default_config
from .server import server
from .version import version


@click.group()
@click.pass_context
def cli(ctx: click.Context) -> None:
    ctx.ensure_object(dict)


def main():
    # Start the Temporalio Worker
    cli.add_command(looper_main, name="looper")
    # start the FastAPI server
    cli.add_command(server)
    # Display version
    cli.add_command(version)
    # Show default config
    cli.add_command(default_config)

    # Parse cmd-line arguments and options
    # pylint: disable=no-value-for-parameter
    cli()


if __name__ == "__main__":
    main()
