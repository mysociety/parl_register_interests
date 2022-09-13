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

    def get_orgs(self, text: str) -> list[str]:
        doc = self.nlp(text)
        return [x.text for x in doc.ents if x.label_ == "ORG"]

    def get_money(self, text: str) -> list[str]:
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
                    yield {
                        "public_whip_id": publicwhip_id,
                        "member_name": membername,
                        "registry_date": date,
                        "category_type": category_type,
                        "category_name": category_name,
                        "free_text": item.text,
                        "latest_entry": is_latest,
                    }


def get_latest_file() -> Path:
    data = Path("data", "raw", "scrapedxml", "regmem")
    files = sorted(list(data.glob("*.xml")))
    return files[-1]


def get_all_data() -> Iterable[dict[str, str]]:
    data = Path("data", "raw", "scrapedxml", "regmem")
    latest = get_latest_file()
    for file in data.glob("*.xml"):
        #  if file is earlier than start of 2021 (file name format regmem2021-01-01.xml), skip
        if file.name < "regmem2021-01-01.xml":
            continue
        rich.print(f"[blue]Processing {file}[/blue]")
        for row in get_data_from_xml(file, is_latest=file == latest):
            yield row


def get_all_data_as_json():

    items = list(get_all_data())
    rich.print(f"[green]Found {len(items)} items[/green]")
    with open(Path("data", "interim", "regmem.json"), "w") as f:
        json.dump(items, f, indent=4)


def add_orgs_to_json():
    """
    Load the stored regmem data and try and extract orgs
    """
    items = json.loads(Path("data", "interim", "regmem.json").read_text())
    df = pd.DataFrame(items).fillna("")
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
    add_orgs_to_json()
