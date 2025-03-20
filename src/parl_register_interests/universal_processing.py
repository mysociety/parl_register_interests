from mysoc_validator.models.interests import RegmemRegister, RegmemEntry, slugify
import pandas as pd
from pathlib import Path
from typing import NamedTuple
from decimal import Decimal


def regmem_to_entries_df(reg: RegmemRegister) -> pd.DataFrame:
    exclude_cols = {
        "annotations",
        "details",
        "id",
        "comparable_id",
        "sub_entries",
        "info_type",
        "item_hash",
        "content_format",
    }

    items = []
    details = []
    for person_entry in reg.persons:
        int_person_id = person_entry.person_id.split("/")[-1]

        for category in person_entry.categories:
            for entry in category.entries:
                entry_id = f"{int_person_id}_{slugify(category.category_id)}_{entry.comparable_id}"
                item = {}
                item["chamber"] = person_entry.chamber
                item["register_date"] = person_entry.published_date
                item["person_id"] = person_entry.person_id
                item["person_name"] = person_entry.person_name
                item["category_id"] = category.category_id
                item["category_name"] = category.category_name
                item["entry_id"] = entry_id
                item["parent_id"] = None
                item |= entry.model_dump(exclude=exclude_cols)
                item["details"] = entry.details.detail_dict()
                items.append(item)
                for sub_entry in entry.sub_entries:
                    sub_entry_id = f"{int_person_id}_{slugify(category.category_id)}_{sub_entry.comparable_id}"

                    subitem = {}
                    subitem["chamber"] = person_entry.chamber
                    subitem["register_date"] = person_entry.published_date
                    subitem["person_id"] = person_entry.person_id
                    subitem["person_name"] = person_entry.person_name
                    subitem["category_id"] = category.category_id
                    subitem["category_name"] = category.category_name
                    subitem["parent_id"] = entry_id
                    subitem["entry_id"] = sub_entry_id
                    subitem |= sub_entry.model_dump(exclude=exclude_cols)
                    subitem["details"] = sub_entry.details.detail_dict()
                    items.append(subitem)

    df = pd.DataFrame(items)

    return df


def regmem_entry_to_details(
    chamber: str, person_id: str, category_id: str, entry: RegmemEntry
) -> list[dict[str, str]]:
    exclude_cols = {"annotations", "sub_detail_groups", "common_key"}

    details = []

    int_person_id = person_id.split("/")[-1]
    entry_id = f"{int_person_id}_{slugify(category_id)}_{entry.comparable_id}"
    for detail in entry.details:
        detail_slug = f"{detail.slug}"
        item = {}
        item["chamber"] = chamber
        item["category_id"] = category_id
        item["person_id"] = person_id
        item["entry_id"] = entry_id
        item["parent_detail_id"] = None
        item["detail_row_id"] = None
        item["detail_id"] = f"{entry_id}_{detail.slug}"
        item |= detail.model_dump(exclude=exclude_cols)
        if detail.type == "container":
            item["value"] = "-"
        item["slug"] = detail_slug
        details.append(item)
        if isinstance(detail.value, list):
            for index, detail_group in enumerate(detail.value):
                for sub_detail in detail_group:
                    item = {}
                    item["chamber"] = chamber
                    item["category_id"] = category_id
                    item["person_id"] = person_id
                    item["entry_id"] = entry_id
                    item["parent_detail_id"] = f"{entry_id}_{detail.slug}"
                    item["detail_row_id"] = f"{entry_id}_{detail.slug}_{index}"
                    item["detail_id"] = (
                        f"{entry_id}_{detail.slug}_{index}_{sub_detail.slug}"
                    )
                    item |= sub_detail.model_dump(exclude=exclude_cols)
                    item["slug"] = f"{detail_slug}_{sub_detail.slug}"
                    details.append(item)

    return details


class DetailDfs(NamedTuple):
    details: pd.DataFrame
    detail_desc: pd.DataFrame


def regmem_to_details(reg: RegmemRegister) -> None | DetailDfs:
    details = []
    for person_entry in reg.persons:
        for category in person_entry.categories:
            for entry in category.entries:
                for sub_entry in [entry] + entry.sub_entries:
                    details.extend(
                        regmem_entry_to_details(
                            person_entry.chamber,
                            person_entry.person_id,
                            category.category_id,
                            sub_entry,
                        )
                    )

    if not details:
        return None

    df = pd.DataFrame(details)

    detail_desc_columns = [
        "chamber",
        "category_id",
        "slug",
        "display_as",
        "description",
        "type",
    ]
    valid = [x for x in detail_desc_columns if x in df.columns]

    detail_desc = df[valid].drop_duplicates()

    # There are limited duplicate descriptions remaining - we need to group by chamber, category_id, slug and then join the descriptions together.

    if "description" in detail_desc.columns:
        detail_desc["description"] = detail_desc["description"].str.strip()

    detail_desc.groupby(["chamber", "category_id", "slug"]).agg(
        {"description": lambda x: ", ".join([y for y in x if y])}
    ).reset_index()

    to_drop = [x for x in ["display_as", "description", "type"] if x in df.columns]

    if to_drop:
        df = df.drop(columns=to_drop)

    return DetailDfs(details=df, detail_desc=detail_desc)


class RegisterCollection(NamedTuple):
    entries: pd.DataFrame
    categories: pd.DataFrame
    details: pd.DataFrame | None
    detail_desc: pd.DataFrame | None


def regmem_to_flat(reg: RegmemRegister):
    """
    Convert the universal regmem to a series of flat DFs
    """

    entries = regmem_to_entries_df(reg)
    category_df = entries[["chamber", "category_id", "category_name"]].drop_duplicates()
    detail_group = regmem_to_details(reg)
    if detail_group:
        details = detail_group.details
        detail_desc = detail_group.detail_desc
    else:
        details = None
        detail_desc = None

    return RegisterCollection(
        entries=entries,
        categories=category_df,
        details=details,
        detail_desc=detail_desc,
    )


def gather_regmems() -> RegisterCollection:
    chambers = [
        "house-of-commons",
        "senedd",
        "scottish-parliament",
        "northern-ireland-assembly",
    ]

    base = Path(
        "data",
        "raw",
        "scrapedjson",
        "universal_format_regmem",
    )

    collections: list[RegisterCollection] = []

    for c in chambers:
        if c == "senedd":
            chamber_base = base / "senedd" / "en"
        else:
            chamber_base = base / c

        # for each json file in the directory - go through these alphabetically

        for f in sorted(chamber_base.glob("*.json")):
            if c == "house-of-commons":
                # break if f.filename < commons-regmem-2024-06-01
                if f.name < "commons-regmem-2024-06-01.json":
                    continue
            regmem = RegmemRegister.from_path(f)
            collections.append(regmem_to_flat(regmem))

    entry_dfs = []
    category_dfs = []
    detail_dfs = []
    detail_desc_dfs = []

    for item in collections:
        entry_dfs.append(item.entries)
        category_dfs.append(item.categories)
        if item.details is not None:
            detail_dfs.append(item.details)
        if item.detail_desc is not None:
            detail_desc_dfs.append(item.detail_desc)

    entries = pd.concat(entry_dfs)
    categories = pd.concat(category_dfs)
    details = pd.concat(detail_dfs)
    detail_descs = pd.concat(detail_desc_dfs)

    # remove easy duplicates
    categories = categories.drop_duplicates()
    detail_descs = detail_descs.drop_duplicates()

    # details - remove duplicates on detail_id preserving latest (will be currently last)
    details = details.drop_duplicates(subset=["detail_id"], keep="last")

    # the value column is a mix of types - we want to make this into strings for compatibility
    details["value"] = details["value"].astype(str)

    # entries is more complicated because we want to preserve some time information
    entries["first_register"] = entries.groupby("entry_id")["register_date"].transform(
        "min"
    )
    entries["last_register"] = entries.groupby("entry_id")["register_date"].transform(
        "max"
    )
    entries = entries.drop_duplicates(subset=["entry_id"], keep="last")
    entries = entries.drop(columns=["register_date"])

    return RegisterCollection(
        entries=entries,
        categories=categories,
        details=details,
        detail_desc=detail_descs,
    )


def store_database_regmem():
    collection = gather_regmems()

    package_path = Path("data", "data_packages", "all_registers_database")

    package_path.mkdir(parents=True, exist_ok=True)

    collection.entries.to_parquet(package_path / "entries.parquet", index=False)
    collection.categories.to_parquet(package_path / "categories.parquet", index=False)
    if collection.details is not None:
        collection.details.to_parquet(package_path / "details.parquet", index=False)
    if collection.detail_desc is not None:
        collection.detail_desc.to_parquet(
            package_path / "detail_desc.parquet", index=False
        )
