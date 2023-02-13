import pandas as pd
from pathlib import Path
from tqdm import tqdm
import xml.etree.ElementTree as ET
import string
from data_common.db import duck_query
import rich
import re


def is_mp_name_line(line: str) -> bool:
    return (
        len(line) > 0
        and line.strip().endswith(")")
        and len([x for x in line.split("(")[0].split(" ") if x]) < 5
        and "," in line
    )


def remove_brackets(text: str) -> str:
    """
    given text like 'hello (text in brackets)'
    remove the the backets and what they contain
    """
    without_brackets = re.sub(r"\([^)]*\)", "", text).strip()
    words = without_brackets.split(" ")
    if len(words) <= 3:  # trying to get rid of all name references
        return ""
    else:
        return without_brackets


def remove_punctuation(text: str):
    """Remove punctuation from text and replace with space"""
    text = text.replace("’", "'")
    # replace all puntuation with a space
    for p in string.punctuation:
        text = text.replace(p, " ")
    return text


def get_word_list(regmem_date: str):
    """
    Get a list of words mentioned in the parquet file
    """

    parquet_path = Path("data", "interim", "regmem")
    # get all unique words in this csv
    regmem_path = parquet_path / (regmem_date + ".parquet")

    desc = duck_query("describe select * from {{ regmem }}", regmem=regmem_path).df()

    serieses = []
    s = 0
    for col in desc["column_name"]:
        d = duck_query(
            "select distinct {{ col }} from {{ regmem }}", regmem=regmem_path, col=col
        ).df()
        s += len(d)
        serieses.append(d[col])

    # combine all series of the dataframe into one big series
    combined = pd.concat(serieses)
    processed_regmem = " ".join(combined.astype(str))

    # all words that made it through to the final output
    processed_words = set(
        remove_punctuation(
            processed_regmem.replace("\\n", " ").replace("\n", " ")
        ).split(" ")
    )
    processed_words = set([x.strip() for x in processed_words])
    return processed_words


def test_all_content_present(start_file: str = ""):
    """
    Open all the original xml files and check that all the content is present in the parquet file

    """
    words = []
    rich.print("[blue]Testing all content transferred[/blue]")
    data = Path("data", "raw", "scrapedxml", "regmem")
    files = sorted(list(data.glob("*.xml")))
    # basic error, not just looking from last parliament
    process_length = len(files)  # does nothing, but can be reduced for debugging
    for xml_path in tqdm(files):
        if start_file and xml_path.name < start_file:
            tqdm.write(f"Skipping processing of {xml_path.name}")
            continue
        date_format_from_path = xml_path.stem.replace("regmem", "")
        processed_words = get_word_list(date_format_from_path)
        processed_words = set([x for x in processed_words if len(x) > 2])
        tree = ET.parse(str(xml_path))
        for item in tree.iter():
            if item.tag in ["span", "em", "br"]:
                continue
            if item.tag == "item":
                for i in item.iter():
                    if i.tag == "br":
                        i.text = " " + (i.text or "")
                # get text from all children of item
                item_text = "".join(item.itertext()).replace("\n", " ")
            else:
                item_text = item.text

            if is_mp_name_line(item_text or ""):
                continue

            if not item_text:
                continue
            item_words = set(
                remove_punctuation(remove_brackets(item_text).strip()).split(" ")
            )
            item_words = set([x.strip() for x in item_words])
            item_words = set([x for x in item_words if len(x) > 2])
            missing_words = item_words.difference(processed_words)
            missing_words = [x for x in missing_words if len(x) > 1]
            if item.text and len(missing_words) > 0:
                raise ValueError(f"error: {xml_path} -  {item_text} - {missing_words}")
        process_length -= 1
        if process_length == 0:
            break
