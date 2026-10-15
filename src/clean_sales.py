"""Clean NSW Valuer General sales data down to Sydney metro residential sales, 2014-2023.

Input : data/raw/nsw_vg/nsw_property_data.csv
Output: data/processed/sydney_sales_clean.parquet
        docs/data_quality_report.md  (row counts removed at each step)
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/nsw_vg/nsw_property_data.csv"
OUT = ROOT / "data/processed/sydney_sales_clean.parquet"
REPORT = ROOT / "docs/data_quality_report.md"

YEAR_MIN, YEAR_MAX = 2014, 2023
PRICE_MIN, PRICE_MAX = 50_000, 20_000_000

# Sydney metro = ABS Greater Sydney minus Central Coast (2250-2263),
# Blue Mountains (2773-2787) and rural Wollondilly (2571-2574).
SYDNEY_METRO_POSTCODES = [(2000, 2234), (2555, 2570), (2745, 2770)]

COLS = [
    "property_id", "council_name", "purchase_price", "address", "post_code",
    "property_type", "strata_lot_number", "area", "area_type", "contract_date",
    "settlement_date", "zoning", "nature_of_property", "primary_purpose",
]


def is_sydney_metro(postcode: pd.Series) -> pd.Series:
    mask = pd.Series(False, index=postcode.index)
    for lo, hi in SYDNEY_METRO_POSTCODES:
        mask |= postcode.between(lo, hi)
    return mask


def main() -> None:
    log: list[tuple[str, int, str]] = []

    def step(df: pd.DataFrame, name: str, why: str) -> pd.DataFrame:
        log.append((name, len(df), why))
        return df

    df = pd.read_csv(RAW, usecols=COLS, low_memory=False)
    df = step(df, "Raw NSW sales", "All records in the Valuer General extract")

    df["contract_date"] = pd.to_datetime(df["contract_date"], errors="coerce")

    # Each dwelling's first recorded sale in the full extract (2001+), before narrowing the window.
    # Used by the repeat-sales index to spot developer / off-the-plan / land first sales of new dwellings.
    valid = df[df["contract_date"].dt.year >= 2001]
    first_sale = (valid.assign(lot=valid["strata_lot_number"].fillna(-1))
                  .groupby(["property_id", "lot"])["contract_date"].min().rename("dwelling_first_sale"))

    df = df[df["contract_date"].dt.year.between(YEAR_MIN, YEAR_MAX)]
    df = step(df, f"Contract year {YEAR_MIN}-{YEAR_MAX}",
              "Agreed analysis window; also removes impossible dates (1877, 2031) and the partial 2024")

    df = df[is_sydney_metro(df["post_code"])]
    df = step(df, "Sydney metro postcodes", "Postcode ranges " +
              ", ".join(f"{a}-{b}" for a, b in SYDNEY_METRO_POSTCODES))

    # The same sale is repeated across weekly extracts; key on the sale itself.
    key = ["property_id", "address", "strata_lot_number", "contract_date", "purchase_price"]
    df = df.drop_duplicates(subset=key)
    df = step(df, "Duplicate sales removed", "Same property, contract date and price appearing more than once")

    df = df[(df["nature_of_property"] == "R") & (df["primary_purpose"] == "RESIDENCE")]
    df = step(df, "Residential only", "Drops vacant land, commercial, retail, car spaces, etc.")

    # Rows sharing street address, date and price are one contract recorded against several lots.
    # For strata, property_id identifies the building and strata_lot_number the lot.
    df["street_address"] = df["address"].str.replace(r"^[^/]*/", "", regex=True)
    grp = df.groupby(["street_address", "contract_date", "purchase_price"])
    n_rows = grp["address"].transform("size")
    n_ids = grp["property_id"].transform("nunique")

    # 2 lots on one title (typically unit + car space / storage lot): one sale, keep one row.
    multi_lot = (n_rows == 2) & (n_ids <= 1)
    df = df[~(multi_lot & df.duplicated(subset=["street_address", "contract_date", "purchase_price"]))]
    df = step(df, "Multi-lot contracts collapsed", "2 lots of one property on one contract (e.g. unit + car space) kept as 1 sale")

    # 3+ dwellings on one contract: bulk deal whose price isn't per dwelling, so drop.
    df = df[~df.index.isin(n_rows[n_rows >= 3].index)]
    df = step(df, "Bulk sales removed (3+ dwellings)", "One combined price across 3+ dwellings is not a per-dwelling price")

    df = df[df["purchase_price"].between(PRICE_MIN, PRICE_MAX)]
    df = step(df, f"Price ${PRICE_MIN:,}-${PRICE_MAX:,}",
              "Removes $0 / nominal transfers (not arm's-length) and implausible extremes")

    # Derived fields
    df["suburb"] = df["address"].str.rsplit(",", n=1).str[-1].str.strip().str.title()
    df["post_code"] = df["post_code"].astype(int)
    df["year"] = df["contract_date"].dt.year
    df["quarter"] = df["contract_date"].dt.to_period("Q").astype(str)
    df["month"] = df["contract_date"].dt.month
    # Source property_type is just "address contains '/'", so strata townhouses/villas are
    # counted as houses. Split them out.
    df["dwelling_type"] = np.select(
        [df["address"].str.contains("/", regex=False), df["strata_lot_number"].notna()],
        ["Unit", "Townhouse/Villa"],
        default="House",
    )
    df["land_sqm"] = np.where(df["area_type"] == "H", df["area"] * 10_000,
                              np.where(df["area_type"] == "M", df["area"], np.nan))
    # Land size is only meaningful for freestanding houses (strata report lot area or nothing)
    df.loc[df["dwelling_type"] != "House", "land_sqm"] = np.nan
    df["price_per_sqm_land"] = df["purchase_price"] / df["land_sqm"]
    df = df.join(first_sale, on=["property_id", df["strata_lot_number"].fillna(-1).rename("lot")])
    # Legacy numeric council codes (pre-2016 mergers): use the suburb's most common current council name
    legacy = df["council_name"].str.fullmatch(r"\d+")
    suburb_council = df[~legacy].groupby("suburb")["council_name"].agg(lambda c: c.mode().iat[0])
    df["council_name"] = df["council_name"].where(~legacy, df["suburb"].map(suburb_council)).fillna("UNKNOWN")
    df["council_name"] = df["council_name"].str.title().str.replace(" Of ", " of ").str.replace("Ku-Ring-Gai", "Ku-ring-gai")

    keep = ["property_id", "address", "suburb", "post_code", "council_name", "dwelling_type", "property_type",
            "purchase_price", "contract_date", "settlement_date", "year", "quarter", "month",
            "land_sqm", "price_per_sqm_land", "zoning", "strata_lot_number", "dwelling_first_sale"]
    df = df[keep].sort_values("contract_date").reset_index(drop=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT, index=False)

    write_report(log, df)
    print(f"Saved {len(df):,} rows -> {OUT.relative_to(ROOT).as_posix()}")


def write_report(log: list[tuple[str, int, str]], df: pd.DataFrame) -> None:
    lines = [
        "# Data Quality Report: NSW Sales → Sydney Metro Residential (2014–2023)",
        "",
        "_Generated by `src/clean_sales.py`._",
        "",
        "## Cleaning funnel",
        "",
        "| Step | Rows remaining | Removed | Rationale |",
        "|---|---:|---:|---|",
    ]
    prev = None
    for name, n, why in log:
        removed = "" if prev is None else f"{prev - n:,}"
        lines.append(f"| {name} | {n:,} | {removed} | {why} |")
        prev = n

    null_pct = (df.isna().mean() * 100).round(1)
    lines += [
        "",
        "## Clean dataset summary",
        "",
        f"- **Rows:** {len(df):,}  ·  **Suburbs:** {df['suburb'].nunique():,}  ·  "
        f"**Postcodes:** {df['post_code'].nunique():,}",
        f"- **Period:** {df['contract_date'].min():%d %b %Y} to {df['contract_date'].max():%d %b %Y}",
        "- **By dwelling type:** " + "  ·  ".join(
            f"{t} {int(n):,} (median ${m:,.0f})" for t, (n, m) in
            df.groupby("dwelling_type")["purchase_price"].agg(["size", "median"]).iterrows()),
        f"- **Repeat-sold properties** (≥2 sales in window, usable for a repeat-sales index): "
        f"{(df.dropna(subset=['property_id']).groupby(['property_id', 'strata_lot_number'], dropna=False).size() >= 2).sum():,}",
        "",
        "### Missing values (clean data)",
        "",
        "| Column | % missing |",
        "|---|---:|",
    ]
    lines += [f"| {c} | {v} |" for c, v in null_pct.items() if v > 0]
    lines += [
        "",
        "## Known limitations",
        "",
        "- **No bedrooms, bathrooms or parking** in this source. Feature-value questions (Q4) use the Domain dataset instead.",
        "- **Medians are affected by what sold (composition bias).** Use the repeat-sales index for true like-for-like growth.",
        "- **Dwelling type:** the source `property_type` only checks for a '/' in the address, so strata townhouses/villas were labelled houses. `dwelling_type` separates House / Townhouse/Villa (strata lot, no unit number) / Unit.",
        "- **Strata identity:** `property_id` is the building (strata plan); a unit is `property_id` + `strata_lot_number`.",
        "- **Council names:** some records carry legacy numeric codes (pre-2016 council mergers); these are mapped to the suburb's most common current council name.",
        "- **Prices are nominal** (not CPI-adjusted) unless stated.",
        "- **Contract date** is used as the sale date, because it reflects when the price was agreed. Settlement is usually 4–6 weeks later.",
        "- Late-2023 sales may be under-counted if they settled after the extract date (Feb 2024).",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
