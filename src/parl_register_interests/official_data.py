from datetime import date as date
from datetime import datetime
from pathlib import Path

import pandas as pd
from mysoc_validator import Popolo
from mysoc_validator.models.popolo import Chamber, IdentifierScheme

RAW_DATA = Path("data", "raw", "external", "official_data")

# ]date(2024, 9, 2)
known_dates = [date(2024, 9, 30)]


def fix_snake_case(s: str) -> str:
    """
    We're being given a column name that might be "ID, "Parent Interest ID", or "JobTitle"
    We want to return "id", "parent_interest_id", or "job_title"
    """
    # are there multiple consqutive uppercase letters?
    multiple_upper = False
    run_count = 0
    for letter in s:
        if letter.isupper():
            run_count += 1
            if run_count > 1:
                multiple_upper = True
                break
        else:
            run_count = 0

    if not multiple_upper:
        s = "".join([" " + c if c.isupper() else c for c in s]).strip()
    while "  " in s:
        s = s.replace("  ", " ")
    s = s.strip()
    s = s.lower()
    s = s.replace(" ", "_")
    return s


def process_register(register_date: date):
    str_date = register_date.strftime("%y%m%d")

    data_path = RAW_DATA / str_date
    data_path.mkdir(parents=True, exist_ok=True)
    package_dir = Path("data", "data_packages", "commons_rmfi")

    popolo = Popolo.from_parlparse()

    all_columns = [
        "id",
        "parent_interest_id",
        "member",
        "party",
        "mnis_id",
        "twfy_id",
        "category",
        "category_code",
        "registration_date",
        "published_date",
        "updated_date",
        "summary",
    ]

    collected_df = []

    for csv in data_path.glob("*.csv"):
        name = csv.stem.replace("PublishedInterest-", "").lower()
        df = pd.read_csv(csv)

        df["category_code"] = name.replace("category_", "")
        # convert columns from camelCase to snake_case - e.g. registrationDate to registration_date
        # where an underscore is added before the capital letter

        df.columns = [fix_snake_case(c) for c in df.columns]
        mnis_ids: list[str] = df["mnis_id"].astype(str).tolist()
        twfy_people = [
            popolo.persons.from_identifier(x, scheme=IdentifierScheme.MNIS)
            for x in mnis_ids
        ]
        twfy_id = [x.reduced_id() for x in twfy_people]
        valid_memberships = [
            x.membership_on_date(register_date, chamber=Chamber.COMMONS)
            for x in twfy_people
        ]
        parties = [
            (x.on_behalf_of_id or "unknown") if x else "unknown"
            for x in valid_memberships
        ]

        df["party"] = parties
        df["twfy_id"] = twfy_id

        # we want to inject the 'party' column before the 'member' column
        current_cols = df.columns.tolist()
        current_cols.remove("party")
        current_cols.remove("twfy_id")
        # add party before member
        new_cols = []
        for col in current_cols:
            if col == "member":
                new_cols.append("party")
            new_cols.append(col)
            if col == "mnis_id":
                new_cols.append("twfy_id")

        df = df[new_cols]

        # for date columns, we want to convert from british format to ISO format string
        date_columns = [x for x in df.columns if x.endswith("date")]
        if "arose_on" in df.columns:
            date_columns.append("arose_on")
        for col in date_columns:
            date_objs = pd.to_datetime(df[col], format="%d/%m/%Y", errors="ignore")  # type: ignore
            date_str = date_objs.apply(
                lambda x: x.date().isoformat() if isinstance(x, datetime) else ""
            )
            date_str = [x if x != "NaT" else "" for x in date_str]
            df[col] = date_str

        df = df.rename(columns={"link_1": "api_link"})
        df.to_parquet(package_dir / f"{name}.parquet")
        df = df[all_columns]
        collected_df.append(df)

    collected_df = pd.concat(collected_df)

    # we want to end up with a file sorted by ID *except* where there is a parent_id
    # in which case, these will appear immediately after the parent_id
    # so we want item 1000 without a parent to have a tuple of (1000, None)
    # and item 2000 with a parent of 1000 to have a tuple of (1000, 2000)

    def get_sort_tuple(row: pd.Series):
        if pd.isnull(row["parent_interest_id"]):
            return (row["id"], 0)
        return (row["parent_interest_id"], row["id"])

    collected_df["sort_tuple"] = collected_df.apply(get_sort_tuple, axis=1)
    collected_df = collected_df.sort_values("sort_tuple")  # type: ignore
    collected_df = collected_df.drop(columns=["sort_tuple"])

    collected_df.to_parquet(package_dir / "overall.parquet")


def process_all_regmem():
    for regmem_date in known_dates:
        process_register(regmem_date)


if __name__ == "__main__":
    process_all_regmem()
