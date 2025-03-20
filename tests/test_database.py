import pandas as pd
from pathlib import Path


package_dir = Path("data", "data_packages", "all_registers_database")


def test_foreign_keys():
    entries = pd.read_parquet(package_dir / "entries.parquet")
    categories = pd.read_parquet(package_dir / "categories.parquet")
    details = pd.read_parquet(package_dir / "details.parquet")
    detail_desc = pd.read_parquet(package_dir / "detail_desc.parquet")

    detail_chamber_and_category_id = details["chamber"] + details["category_id"]
    category_chamber_and_category_id = categories["chamber"] + categories["category_id"]
    entry_chamber_and_category_id = entries["chamber"] + entries["category_id"]
    detail_desc_chamber_and_slug = detail_desc["chamber"] + detail_desc["slug"]
    detail_chamber_and_slug = details["chamber"] + details["slug"]

    # check that all detail_ids in details are in detail_desc
    assert details["slug"].isin(detail_desc["slug"]).all()

    # check that all entry categories in categories are in entries
    assert entry_chamber_and_category_id.isin(category_chamber_and_category_id).all()

    # check that all detail category_id in details are in categories
    assert detail_chamber_and_category_id.isin(category_chamber_and_category_id).all()

    # check that all detail_ids in details are in entries
    assert details["entry_id"].isin(entries["entry_id"]).all()

    # check that all category_ids in categories are in details
    assert details["category_id"].isin(categories["category_id"]).all()

    # check that all interest_ids in entries are in details
    assert details["entry_id"].isin(entries["entry_id"]).all()

    # check that all interest_ids in entries are in details
    assert details["entry_id"].isin(entries["entry_id"]).all()

    # check that all detail_ids in details are in detail_desc
    assert detail_chamber_and_slug.isin(detail_desc_chamber_and_slug).all()
