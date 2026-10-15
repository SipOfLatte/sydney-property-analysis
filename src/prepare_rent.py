"""Parse NSW DCJ quarterly rent tables into one tidy CSV of Sydney metro rents.

Input : data/external/rent/rent_<year>Q4.xlsx   (DCJ "Rent and Sales Report", Postcode sheet)
Output: data/exports/rent_by_postcode.csv

Source: NSW Department of Communities and Justice, Rent and Sales Report (new bonds lodged).
Suppressed cells: "s" = 30 or fewer bonds lodged, "-" = 10 or fewer. Both are dropped.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RENT_DIR = ROOT / "data/external/rent"
OUT = ROOT / "data/exports/rent_by_postcode.csv"

# Same Sydney metro definition as the sales pipeline (src/clean_sales.py)
SYDNEY_METRO_POSTCODES = [(2000, 2234), (2555, 2570), (2745, 2770)]
# DCJ dwelling types -> the segments used throughout the analysis
SEGMENT = {"House": "House", "Flat/Unit": "Unit/Townhouse", "Townhouse": "Unit/Townhouse"}


def read_quarter(path: Path, year: int) -> pd.DataFrame:
    raw = pd.read_excel(path, "Postcode", header=None)
    header = next(i for i in range(20) if str(raw.iloc[i, 0]).strip() == "Postcode")
    df = pd.read_excel(path, "Postcode", header=header)
    df.columns = [str(c).replace("\n", " ").strip() for c in df.columns]
    bedrooms = "Number of Bedrooms" if "Number of Bedrooms" in df.columns else "Bedroom Numbers"
    df = df.rename(columns={
        bedrooms: "bedrooms", "Dwelling Types": "dwelling", "Postcode": "post_code",
        "Median Weekly Rent for New Bonds $": "median_weekly_rent",
        "New Bonds Lodged No.": "new_bonds", "Total Bonds Held No.": "total_bonds",
    })
    df["year"] = year
    keep = ["year", "post_code", "dwelling", "bedrooms", "median_weekly_rent", "new_bonds", "total_bonds"]
    return df[keep]


def main() -> None:
    frames = []
    for path in sorted(RENT_DIR.glob("rent_*Q4.xlsx")):
        year = int(path.stem.split("_")[1][:4])
        frames.append(read_quarter(path, year))
    rent = pd.concat(frames, ignore_index=True)

    rent["post_code"] = pd.to_numeric(rent.post_code, errors="coerce")
    in_sydney = pd.Series(False, index=rent.index)
    for lo, hi in SYDNEY_METRO_POSTCODES:
        in_sydney |= rent.post_code.between(lo, hi)
    rent = rent[in_sydney & rent.dwelling.isin(SEGMENT)]

    # "s" / "-" mark suppressed small samples
    for col in ["median_weekly_rent", "new_bonds", "total_bonds"]:
        rent[col] = pd.to_numeric(rent[col].astype(str).str.replace(",", ""), errors="coerce")
    rent = rent.dropna(subset=["median_weekly_rent"])
    rent["segment"] = rent.dwelling.map(SEGMENT)
    rent["post_code"] = rent.post_code.astype(int)

    # Segment-level rent: weight each dwelling type's median by the bonds behind it
    weights = rent.new_bonds.fillna(0) + 1
    rent["_w"] = weights
    rent["_wr"] = rent.median_weekly_rent * weights
    seg = (rent.groupby(["year", "post_code", "segment", "bedrooms"])
                .agg(_wr=("_wr", "sum"), _w=("_w", "sum"), new_bonds=("new_bonds", "sum"),
                     total_bonds=("total_bonds", "sum"))
                .assign(median_weekly_rent=lambda d: (d._wr / d._w).round(0))
                .drop(columns=["_wr", "_w"]).reset_index())

    OUT.parent.mkdir(parents=True, exist_ok=True)
    seg.to_csv(OUT, index=False)
    headline = seg[seg.bedrooms == "Total"]
    print(f"Saved {len(seg):,} rows -> {OUT.relative_to(ROOT).as_posix()}")
    print(headline.groupby(["year", "segment"]).median_weekly_rent.median().unstack().to_string())


if __name__ == "__main__":
    main()
