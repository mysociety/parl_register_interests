import re
import subprocess
from functools import lru_cache
from pathlib import Path

import rich


@lru_cache
def download_regmem():
    """
    Download all regme.xml files of format regmem2022-05-03.xml of 2021 or later to data/raw.
    """
    rich.print("[blue]Downloading regmem files[/blue]")
    cmd = "rsync -az --progress --exclude '.svn' --exclude 'tmp/' --relative data.theyworkforyou.com::parldata/scrapedxml/regmem/* data/raw"
    subprocess.run(cmd.split(" "))
    cmd = "rsync -az --progress --exclude '.svn' --exclude 'tmp/' --relative data.theyworkforyou.com::parldata/scrapedjson/universal_format_regmem/* data/raw"
    subprocess.run(cmd.split(" "))
    rich.print("[green]Done[/green]")
    fix_known_errors()


def fix_known_errors():
    # fix category formatting error

    folder = Path("data", "raw", "scrapedxml", "regmem")

    xml_files = sorted(list(folder.glob("*.xml")))

    for xml_file in xml_files:
        # if xml_file.name != "regmem2015-01-26.xml":
        #    continue

        # older files are in cp1252 encoding but more recent ones are utf-8
        # try utf-8 first

        try:
            txt = xml_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            txt = xml_file.read_text(encoding="cp1252")

        regex_pattern = r"<item><strong>(\d+\.\s[A-Za-z\s]+)<\/strong><\/item>"
        matches = re.finditer(regex_pattern, txt, re.MULTILINE)
        loop = 0
        for matchNum, match in enumerate(matches, start=1):
            # get original text
            old_text = match.group(0)
            item = match.group(1)
            # get category number
            cat_num = item.split(".")[0]
            # get category name
            cat_name = item.split(".")[1].strip()
            # create new text
            new_text = f'<category type="{cat_num}" name="{cat_name}"><inject loop="{loop}"></inject>'

            loop += 1
            bad_text_loc = txt.find(old_text)
            close_category = True
            no_previous_category = False
            previous_regmem = txt.rfind("<regmem", 0, bad_text_loc)
            if txt[previous_regmem:bad_text_loc].count("<category") == txt[
                previous_regmem:bad_text_loc
            ].count("</category"):
                no_previous_category = True

            if (
                txt[bad_text_loc - 30 : bad_text_loc].count("</item>") > 0
                and no_previous_category is False
            ):
                close_category = False
                new_text = f"</category>{new_text}"

            previous_regmem = txt.rfind("<regmem", 0, bad_text_loc)

            if txt[previous_regmem:bad_text_loc].count("<record") > 0:
                new_text = f"</record>{new_text}<record>"
            txt = txt[:bad_text_loc] + new_text + txt[bad_text_loc + len(old_text) :]
            cat_loc = txt.find(new_text) + len(new_text)
            next_cat_loc = txt.find("<category", cat_loc)
            next_regmem_loc = txt.find("</regmem", cat_loc)
            if close_category is False:
                continue
            if next_regmem_loc < next_cat_loc:
                txt = txt[:next_regmem_loc] + "</category>" + txt[next_regmem_loc:]
            else:
                # check there isn't a double close
                if txt[next_cat_loc - 20 : next_cat_loc].count("</category>") != 0:
                    continue
                txt = txt[:next_cat_loc] + "</category>" + txt[next_cat_loc:]

        first_cat_desc = '<category type="1" name="Directorships">'
        second_cat_desc = (
            '<category type="2" name="Remunerated employment, office, profession etc">'
        )

        # for each mention of first_cat_desc, check category is closed before second_cat_desc
        # if not, close it
        start = 0
        while start != -1:
            start = txt.find(first_cat_desc, start)
            if start == -1:
                break
            end = txt.find("</category>", start)
            if end == -1:
                break
            second_item_loc = txt.find(second_cat_desc, start, end)
            if second_item_loc != -1:
                txt = txt[:second_item_loc] + "</category>" + txt[second_item_loc:]
            start = end + 1

        # fix to object order
        start = 0
        while start != -1:
            regmem_loc = txt.find("<regmem", start)
            if regmem_loc == -1:
                break
            start = regmem_loc + 1
            next_record = txt.find("<record", regmem_loc, regmem_loc + 1000)
            next_category = txt.find("<category", regmem_loc, regmem_loc + 1000)
            next_record_close = txt.find("</record", regmem_loc, next_category)

            # if either is -1 continue
            if next_record == -1 or next_category == -1:
                continue
            if (
                next_record < next_category and next_record_close == -1
            ):  # if opened in the wrong order
                print("Fixing wrong order")
                # delete next mention of '<record>'
                record_loc = txt.find("<record>", regmem_loc)
                txt = txt[:record_loc] + txt[record_loc + 8 :]
                # insert record beofre next item entry
                item_loc = txt.find("<item>", record_loc)
                txt = txt[:item_loc] + "<record>" + txt[item_loc:]

        if loop > 0:
            pass
            xml_file.write_text(txt, encoding="cp1252")


if __name__ == "__main__":
    download_regmem()
