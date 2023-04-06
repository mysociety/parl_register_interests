import hashlib
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable

import pandas as pd
import rich
import spacy
from tqdm import tqdm

from data_common.db import duck_query
from .validate import test_all_content_present, is_mp_name_line


start_file = "regmem2000-01-01.xml"


class OrgExtractor:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_lg")
        self.cache: pd.DataFrame
        self.load_cache()

    def store_cache(self):
        cache_file = Path("data", "interim", "nlp.cache.parquet")
        self.cache.to_parquet(cache_file)

    def load_cache(self):
        cache_file = Path("data", "interim", "nlp.cache.parquet")
        if cache_file.exists():
            df = pd.read_parquet(cache_file)
        else:
            df = pd.DataFrame({"hash": [], "extracted_orgs": [], "extracted_orgs": []})
        print(f"Cache loaded, {len(df)} rows")
        self.cache = df.set_index("hash")

    def pipeline(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process the free_text column from the data frame all at once
        """

        # hash the text and get previous values from cache (if present)
        df["hash"] = df["free_text"].apply(
            lambda x: hashlib.md5(x.encode()).hexdigest()[:10]
        )
        df = df.merge(self.cache, on="hash", how="left")

        # only run the pipeline on new text
        ndf = df[(df["extracted_orgs"].isna()) | (df["extracted_orgs"].isna())]

        all_orgs = []
        all_money = []
        t = tqdm(total=len(ndf))
        for doc in self.nlp.pipe(
            ndf["free_text"],
            disable=["lemmatizer", "textcat"],
            batch_size=200,
            n_process=1,
        ):
            t.update()
            orgs = [x.text for x in doc.ents if x.label_ == "ORG"]
            money = [x.text for x in doc.ents if x.label_ == "MONEY"]
            all_orgs.append(orgs)
            all_money.append(money)
        t.close()

        new_orgs = pd.Series(all_orgs, index=ndf.index, dtype="object")
        new_money = pd.Series(all_money, index=ndf.index, dtype="object")

        # if columns don't exist create blank ones
        if "extracted_orgs" not in df.columns:
            df["extracted_orgs"] = pd.Series(dtype="object")
        if "extracted_sum" not in df.columns:
            df["extracted_sum"] = pd.Series(dtype="object")
        df["extracted_orgs"].update(new_orgs)
        df["extracted_sum"].update(new_money)

        # get new cache from df
        self.cache = df[["hash", "extracted_orgs", "extracted_sum"]]
        self.cache = self.cache.drop_duplicates("hash")
        self.store_cache()

        df = df.drop(columns=["hash"])

        return df


def remove_duplicates(items: list[str]) -> list[str]:
    """
    This list of items may contain complete duplicate lines, or lines that are entirely contained within other lines.
    This function removes these duplicates - preferring the fuller version of the line.
    """
    items = [x.strip() for x in items]
    # deduplicate list but maintain order
    items = list(dict.fromkeys(items))
    # remove items that are contained within other items
    for item in items:
        for other_item in items:
            if item != other_item and item in other_item:
                if item in items:
                    items.remove(item)
    return items


def get_data_from_xml(xml_path: Path, is_latest: bool) -> Iterable[dict[str, str]]:
    """
    Given a register XML, return in a nice data structure
    """
    tree = ET.parse(str(xml_path))
    root = tree.getroot()
    for person in root.iter():
        if person.tag != "regmem":
            continue
        publicwhip_id = person.get("personid", "")
        membername = person.get("membername", "")
        date = person.get("date")
        for category in person:
            if category.tag == "record":
                meta_items = [x.text for x in category.iter()]
                if "Nil" in meta_items:
                    yield {
                        "public_whip_id": publicwhip_id,
                        "member_name": membername,
                        "registry_date": date,
                        "category_name": "No declared interests",
                        "free_text": "Nil interests were declared",
                        "latest_entry": is_latest,
                    }
                else:

                    for item in category:
                        # check this isn't just the MP name
                        if is_mp_name_line(item.text or ""):
                            continue

                        if item.tag == "item":
                            text = "".join(category.itertext())
                            if text:
                                yield {
                                    "public_whip_id": publicwhip_id,
                                    "member_name": membername,
                                    "registry_date": date,
                                    "category_name": "Uncatagorised (format error)",
                                    "free_text": text,
                                    "latest_entry": is_latest,
                                }

            if category.tag == "item":
                if category.text and "not taken his heat" in category.text:
                    yield {
                        "public_whip_id": publicwhip_id,
                        "member_name": membername,
                        "registry_date": date,
                        "category_name": "No declared interests",
                        "free_text": "Not taken heat",
                        "latest_entry": is_latest,
                    }
                else:
                    # get text from this item and all children
                    text = "".join(category.itertext())
                    if text:
                        yield {
                            "public_whip_id": publicwhip_id,
                            "member_name": membername,
                            "registry_date": date,
                            "category_name": "Uncatagorised (format error)",
                            "free_text": text,
                            "latest_entry": is_latest,
                        }

            if category.tag != "category":
                continue
            category_type = category.get("type", "")
            category_name = category.get("name", "")
            for record in category:
                if (
                    record.tag == "item"
                ):  # fix for old style xml where item is not wrapped in a record
                    record = [record]
                for item in record:
                    for i in item.iter():
                        if i.tag == "br":
                            i.text = " " + (i.text or "")
                    lines = item.itertext()
                    free_text = "".join(lines)
                    yield {
                        "public_whip_id": publicwhip_id,
                        "member_name": membername,
                        "registry_date": date,
                        "category_name": category_name,
                        "free_text": free_text,
                        "latest_entry": is_latest,
                    }


def get_latest_file() -> Path:
    """
    Get the very latest version of the register
    """
    data = Path("data", "raw", "scrapedxml", "regmem")
    files = sorted(list(data.glob("*.xml")))
    return files[-1]


def reduce_data() -> pd.DataFrame:
    """
    The all time register is big, this function reduces all the duplicate entries and puts a time range
    that an MP was declaring a specific interest.
    Minor changes in text will create a new entry, but this is mostly about reducing size
    """
    rich.print("[blue]Reducing data[/blue]")
    parquet_path = Path("data", "interim", "regmem", "*.parquet")

    all_query = "select max(registry_date) as latest_register from {{ parquet_path }}"

    df = duck_query(
        "group_same_entry.sql",
        parquet_path=parquet_path,
    ).df()

    # move member_name column to after public_whip_id column
    cols = list(df.columns)
    cols.insert(1, cols.pop(cols.index("member_name")))
    df = df.loc[:, cols]

    max_register = duck_query(all_query, parquet_path=parquet_path).str()
    df["new_in_latest"] = df["earliest_declaration"] == max_register
    df["declared_in_latest"] = df["latest_declaration"] == max_register

    print(f"Latest register date: {max_register}, items: {len(df)}")
    return df


def get_all_data(quiet: bool = False) -> Iterable[pd.DataFrame]:
    data = Path("data", "raw", "scrapedxml", "regmem")
    latest = get_latest_file()
    files = sorted(list(data.glob("*.xml")))
    for file in tqdm(files):
        # allow excluding older files as needed
        if file.name < start_file:
            continue
        if not quiet:
            rich.print(f"[blue]Processing {file}[/blue]")
        data = get_data_from_xml(file, is_latest=file == latest)
        yield pd.DataFrame(data)  # type: ignore


def get_all_data_as_parquet():
    """
    Save the full set of data as intermediate files
    """
    count = 0
    dest = Path("data", "interim", "regmem")
    if not dest.exists():
        dest.mkdir(parents=True)
    for df in get_all_data(quiet=True):
        count += len(df)
        date = df["registry_date"].unique()[0]
        df.to_parquet(
            dest / f"{date}.parquet",
            index=False,
        )
    rich.print(f"[green]Wrote {count} items[/green]")


def add_orgs_data():
    """
    Load the stored regmem data and try and extract orgs
    """
    df = reduce_data()
    rich.print("[blue]Extracting orgs and money[/blue]")
    oe = OrgExtractor()
    df = oe.pipeline(df)
    # print all items that aren't iterables
    df["extracted_orgs"] = df["extracted_orgs"].apply("; ".join)
    df["extracted_sum"] = df["extracted_sum"].apply("; ".join)
    rich.print("[green]Done[/green]")
    df.to_parquet(
        Path("data", "interim", "processed_regmem.parquet"),
        index=False,
    )


class data_processor:

    iteration = 0

    @classmethod
    def process_data(cls):
        """
        Only create the general data once
        """
        cls.iteration += 1
        if cls.iteration > 1:
            return
        get_all_data_as_parquet()
        test_all_content_present(start_file)
        add_orgs_data()


def process_data_all_time():
    data_processor.process_data()
    origin = Path("data", "interim", "processed_regmem.parquet")
    dest = Path(
        "data", "data_packages", "all_time_register", "register_of_interests.parquet"
    )
    shutil.copy(origin, dest)


def process_data_latest():
    data_processor.process_data()
    origin = Path("data", "interim", "processed_regmem.parquet")
    dest = Path(
        "data", "data_packages", "latest_register", "register_of_interests.parquet"
    )
    df = pd.read_parquet(origin)
    df = df[df["declared_in_latest"] == True]
    df = df.drop(columns=["declared_in_latest"])
    df.to_parquet(dest, index=False)
