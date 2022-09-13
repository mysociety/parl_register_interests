import subprocess
import rich


def download_regmem():
    """
    Download all regme.xml files of format regmem2022-05-03.xml of 2021 or later to data/raw.
    """
    rich.print("[blue]Downloading regmem files[/blue]")
    cmd = "rsync -az --progress --exclude '.svn' --exclude 'tmp/' --relative data.theyworkforyou.com::parldata/scrapedxml/regmem/* data/raw"
    subprocess.run(cmd.split(" "))
    rich.print("[green]Done[/green]")


if __name__ == "__main__":
    download_regmem()
