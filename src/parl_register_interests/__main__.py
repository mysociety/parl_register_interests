import rich_click as click
from .download import download_regmem
from .process import process_data_all_time, process_data_2019, get_data_from_xml
from pathlib import Path


def download_and_build():
    download_regmem()
    process_data_all_time()
    process_data_2019()


def download_and_build_all_time():
    download_regmem()
    process_data_all_time()


def download_and_build_2019():
    download_regmem()
    process_data_2019()


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
    download_and_build()


if __name__ == "__main__":
    main()
