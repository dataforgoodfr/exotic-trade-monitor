import click

from ingestion.sources import SOURCES


@click.command()
@click.argument(
    "sources",
    nargs=-1,
    type=click.Choice(list(SOURCES.keys()), case_sensitive=False),
)
def main(sources: tuple[str, ...]) -> None:
    """Run data ingestion pipelines (all sources by default, or specific sources)."""
    selected = sources or tuple(SOURCES.keys())
    for name in selected:
        click.echo(f"=== Running ingestion: {name} ===")
        SOURCES[name.lower()]()


if __name__ == "__main__":
    main()
