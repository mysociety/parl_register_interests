import rich_click as click
from .download import download_regmem
from .process import process_data_all_time, process_data_latest, get_data_from_xml
from pathlib import Path


def download_and_build():
    download_regmem()
    process_data_all_time()
    process_data_latest()


def download_and_build_all_time():
    download_regmem()
    process_data_all_time()


def download_and_build_latest():
    download_regmem()
    process_data_latest()


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


@cli.command()
def test():
    test_file = Path("data", "raw", "scrapedxml", "regmem", "regmem2023-02-06.xml")
    for x in get_data_from_xml(test_file, False):
        pass


if __name__ == "__main__":
    main()
