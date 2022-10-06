import xml.etree.ElementTree as ET
from typing import Iterable
import json
from pathlib import Path
import rich
import pandas as pd
import json
import spacy
from tqdm import tqdm

tqdm.pandas()


class OrgExtractor:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")
        self.money_cache = {}
        self.org_cache = {}
        self.load_cache()

    def __del__(self):
        self.store_cache()

    def store_cache(self):
        cache_dir = Path("data", "interim")

        with open(cache_dir / "org_cache.json", "w") as f:
            json.dump(self.org_cache, f, indent=4)
        with open(cache_dir / "money_cache.json", "w") as f:
            json.dump(self.money_cache, f, indent=4)

    def load_cache(self):
        cache_dir = Path("data", "interim")
        org_cache_file = cache_dir / "org_cache.json"
        money_cache_file = cache_dir / "money_cache.json"
        if org_cache_file.exists():
            with open(cache_dir / "org_cache.json", "r") as f:
                self.org_cache = json.load(f)
        if money_cache_file.exists():
            with open(cache_dir / "money_cache.json", "r") as f:
                self.money_cache = json.load(f)

    def get_orgs(self, text: str) -> list[str]:
        if text in self.org_cache:
            return self.org_cache[text]
        orgs = self._get_orgs(text)
        self.org_cache[text] = orgs
        return orgs

    def get_money(self, text: str) -> list[str]:
        if text in self.money_cache:
            return self.money_cache[text]
        money = self._get_money(text)
        self.money_cache[text] = money
        return money

    def _get_orgs(self, text: str) -> list[str]:
        doc = self.nlp(text)
        return [x.text for x in doc.ents if x.label_ == "ORG"]

    def _get_money(self, text: str) -> list[str]:
        doc = self.nlp(text)
        return [x.text for x in doc.ents if x.label_ == "MONEY"]


def get_data_from_xml(xml_path: Path, is_latest: bool) -> Iterable[dict[str, str]]:
    tree = ET.parse(str(xml_path))
    root = tree.getroot()
    for person in root:
        if person.tag != "regmem":
            continue
        publicwhip_id = person.get("personid", "")
        membername = person.get("membername", "")
        date = person.get("date")
        for category in person:
            if category.tag != "category":
                continue
            category_type = category.get("type", "")
            category_name = category.get("name", "")
            for record in category:
                for item in record:
                    lines: list[str] = [item.text] if item.text else []
                    for child in item:
                        if child.text:
                            lines.append(child.text)
                    free_text = "\n".join(lines)

                    yield {
                        "public_whip_id": publicwhip_id,
                        "member_name": membername,
                        "registry_date": date,
                        "category_name": category_name,
                        "free_text": free_text,
                        "latest_entry": is_latest,
                    }


def get_latest_file() -> Path:
    data = Path("data", "raw", "scrapedxml", "regmem")
    files = sorted(list(data.glob("*.xml")))
    return files[-1]


def reduce_data() -> pd.DataFrame:
    """
    Take the register and reduce to unique free text
    """
    rich.print("[blue]Reducing data[/blue]")
    df = pd.read_json(Path("data", "interim", "regmem.json"))
    latest_register = df["registry_date"].max()

    def reduce_entry(df: pd.DataFrame, latest_register: str):
        earliest_date = df["registry_date"].min()
        latest_date = df["registry_date"].max()
        if earliest_date == latest_register:
            earliest_date += " (latest)"
        if latest_date == latest_register:
            latest_date += " (latest)"
        public_whip_id = df["public_whip_id"].unique()[0]
        member_name = df["member_name"].unique()[0]
        category_name = df["category_name"].unique()[0]
        free_text = df["free_text"].unique()[0]
        return pd.Series(
            {
                "public_whip_id": public_whip_id,
                "member_name": member_name,
                "category_name": category_name,
                "earliest_declaration": earliest_date,
                "latest_declaration": latest_date,
                "free_text": free_text,
            }
        )

    d = (
        df.groupby(["public_whip_id", "free_text"])
        .apply(reduce_entry, latest_register=latest_register)  # type: ignore
        .reset_index(drop=True)
        .sort_values(["public_whip_id", "latest_declaration"], ascending=False)  # type: ignore
    )
    rich.print(f"[green]Reduced to {len(d)} items[/green]")
    return d


def get_all_data() -> Iterable[dict[str, str]]:
    data = Path("data", "raw", "scrapedxml", "regmem")
    latest = get_latest_file()
    for file in data.glob("*.xml"):
        #  if file is earlier than start of 2020 (file name format regmem2020-01-01.xml), skip
        if file.name < "regmem2020-01-01.xml":
            continue
        rich.print(f"[blue]Processing {file}[/blue]")
        for row in get_data_from_xml(file, is_latest=file == latest):
            yield row


def get_all_data_as_json():

    items = list(get_all_data())
    rich.print(f"[green]Found {len(items)} items[/green]")
    with open(Path("data", "interim", "regmem.json"), "w") as f:
        json.dump(items, f, indent=4)


def add_orgs_data():
    """
    Load the stored regmem data and try and extract orgs
    """
    df = reduce_data()
    oe = OrgExtractor()
    rich.print("[blue]Extracting orgs[/blue]")
    df["extracted_orgs"] = df["free_text"].progress_apply(oe.get_orgs).apply("; ".join)
    rich.print("[blue]Extracting money[/blue]")
    df["extracted_sum"] = df["free_text"].progress_apply(oe.get_money).apply("; ".join)
    rich.print("[green]Done[/green]")
    df.to_csv(
        Path("data", "data_packages", "regmem", "processed_regmem.csv"), index=False
    )


def process_data():
    get_all_data_as_json()
    add_orgs_data()
