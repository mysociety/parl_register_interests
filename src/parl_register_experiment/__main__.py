import rich_click as click
from .download import download_regmem
from .process import get_all_data_as_json, process_data


@click.group()
def cli():
    pass


def main():
    cli()


@cli.command()
def download():
    download_regmem()


@cli.command()
def build():
    # download_regmem()
    process_data()


if __name__ == "__main__":
    main()
