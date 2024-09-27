import hashlib
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import rich
import spacy
from data_common.db import duck_query
from tqdm import tqdm

from .validate import is_mp_name_line, test_all_content_present

start_file = "regmem2000-01-01.xml"


class OrgExtractor:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_md")
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
            df = pd.DataFrame({"hash": [], "extracted_orgs": [], "extracted_sum": []})
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
        ndf = df[(df["extracted_orgs"].isna()) | (df["extracted_sum"].isna())]

        # so if the free_text column is longer than 500 characters
        # we need to split into a list of string showing different
        # parts of the text.

        # we then need to feed through the nlp pipeline in a way we can
        # piece this back together afterwards
        threshold = 500

        # so potential problem here on the split lines
        def split_text(text: str) -> list[str]:
            if len(text) > threshold:
                return [text[i : i + threshold] for i in range(0, len(text), threshold)]
            else:
                return [text]

        nlp_df = pd.DataFrame(
            {"free_text": ndf["free_text"], "original_index": ndf.index}
        )
        nlp_df["free_text_split"] = nlp_df["free_text"].apply(split_text)
        nlp_df = nlp_df.explode("free_text_split").reset_index(drop=True)

        print(f"Split {len(ndf)} entries into {len(nlp_df)} rows for NLP processing")

        all_orgs = []
        all_money = []
        t = tqdm(total=len(nlp_df))

        # need to write the ongoing orgs and money to an file to save on memory
        # then read back in and merge back into the dataframe
        import tempfile

        temp_dir = tempfile.mkdtemp()
        temp_file = Path(temp_dir, "nlp.tsv")

        with open(temp_file, "w") as f:
            for doc in self.nlp.pipe(
                nlp_df["free_text_split"],
                disable=["lemmatizer", "textcat"],
                batch_size=100,
                n_process=1,
            ):
                t.update()
                orgs = [x.text for x in doc.ents if x.label_ == "ORG"]
                money = [x.text for x in doc.ents if x.label_ == "MONEY"]
                to_write = "\t".join(orgs) + "||||" + "\t".join(money)
                while "\n" in to_write:
                    to_write = to_write.replace("\n", " ")
                f.write(to_write + "\n")
            t.close()

            # now read back in the file

        with open(temp_file, "r") as f:
            for line in f:
                line_stored = line.strip().split("||||")
                if len(line_stored) == 1:
                    orgs = line_stored[0]
                    money = ""
                else:
                    orgs, money = line_stored
                all_orgs.append(orgs.split("\t"))
                all_money.append(money.split("\t"))

        print(len(all_orgs))
        print(len(all_money))

        # delete temp dir
        shutil.rmtree(temp_dir)
        nlp_df["new_orgs"] = pd.Series(all_orgs, index=nlp_df.index, dtype="object")
        nlp_df["new_money"] = pd.Series(all_money, index=nlp_df.index, dtype="object")

        # now collapse nlp_df based on original index
        # want to join the orgs and money together (these are both lists) and remove duplicates

        def join_lists(items: list[list[str]]) -> list[str]:
            # merge multiple lists
            all_items: list[str] = []
            for item in items:
                all_items.extend(item)
            return remove_duplicates(all_items)

        # groupby also sets the index to the grouped column
        nlp_df = nlp_df.groupby("original_index").agg(
            {"new_orgs": join_lists, "new_money": join_lists}
        )

        # if columns don't exist create blank and merge back in the results
        if "extracted_orgs" not in df.columns:
            df["extracted_orgs"] = pd.Series(dtype="object")
        if "extracted_sum" not in df.columns:
            df["extracted_sum"] = pd.Series(dtype="object")
        df["extracted_orgs"].update(nlp_df["new_orgs"])
        df["extracted_sum"].update(nlp_df["new_money"])

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


def get_data_from_xml(xml_path: Path, is_latest: bool) -> Iterable[dict[str, Any]]:
    """
    Given a register XML, return in a nice data structure
    """
    tree = ET.parse(str(xml_path))
    root = tree.getroot()
    for person in root.iter():
        if person.tag != "regmem":
            continue
        if isinstance(person, ET.Element):
            person = person
        else:
            continue
        publicwhip_id = person.get("personid", "")
        membername = person.get("membername", "")
        date = person.get("date")
        for category in person:
            source_order = 1
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
                        "source_order": source_order,
                    }
                    source_order += 1
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
                                    "source_order": source_order,
                                }
                                source_order += 1
            if category.tag == "item":
                if category.text and "not taken his heat" in category.text:
                    yield {
                        "public_whip_id": publicwhip_id,
                        "member_name": membername,
                        "registry_date": date,
                        "category_name": "No declared interests",
                        "free_text": "Not taken heat",
                        "latest_entry": is_latest,
                        "source_order": source_order,
                    }
                    source_order += 1
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
                            "source_order": source_order,
                        }
                        source_order += 1

            if category.tag != "category":
                continue
            category.get("type", "")
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
                        "source_order": source_order,
                    }
                    source_order += 1


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

    df = df.drop(columns=["source_order"])

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


def process_data_2019():
    data_processor.process_data()
    origin = Path("data", "interim", "processed_regmem.parquet")
    dest = Path(
        "data", "data_packages", "parliament_2019", "register_of_interests.parquet"
    )
    df = pd.read_parquet(origin)
    mask = (df["latest_declaration"] >= "2019-12-12") & ( # type: ignore
        df["latest_declaration"] < "2024-07-01"
    )  # type: ignore
    df[mask].to_parquet(dest, index=False)


def process_data_2024():
    data_processor.process_data()
    origin = Path("data", "interim", "processed_regmem.parquet")
    dest = Path(
        "data", "data_packages", "parliament_2024", "register_of_interests.parquet"
    )
    df = pd.read_parquet(origin)
    mask = df["latest_declaration"] >= "2024-07-01"  # type: ignore
    df[mask].to_parquet(dest, index=False)
