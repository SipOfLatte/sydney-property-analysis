"""Extract one centroid per suburb from the Domain listings, for the dashboard map.

Input : data/raw/domain/domain_properties.csv   (Kaggle: alexlau203/sydney-house-prices)
Output: data/exports/suburb_coords.csv

The Domain file carries suburb-level attributes repeated on every listing (the same
latitude, longitude and CBD distance for every property in a suburb), so one row per
suburb is all the map needs. Coordinates are suburb centroids, not property locations.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/raw/domain/domain_properties.csv"
OUT = ROOT / "data/exports/suburb_coords.csv"

# Same Sydney metro window as the sales pipeline, as a coordinate box (the Domain file
# reaches the Central Coast and the Southern Highlands, which the analysis excludes).
LAT_MIN, LAT_MAX = -34.15, -33.55
LNG_MIN, LNG_MAX = 150.50, 151.40


def main() -> None:
    d = pd.read_csv(SRC, usecols=["suburb", "suburb_lat", "suburb_lng", "km_from_cbd",
                                  "suburb_population", "suburb_median_income"])
    coords = (d.groupby("suburb")
               .agg(lat=("suburb_lat", "median"), lng=("suburb_lng", "median"),
                    km_from_cbd=("km_from_cbd", "median"),
                    population=("suburb_population", "median"),
                    median_income=("suburb_median_income", "median"))
               .round({"lat": 5, "lng": 5, "km_from_cbd": 1})
               .reset_index())

    outside = ~(coords.lat.between(LAT_MIN, LAT_MAX) & coords.lng.between(LNG_MIN, LNG_MAX))
    print(f"Dropped {outside.sum()} suburbs outside the Sydney metro box "
          f"(e.g. {', '.join(coords.suburb[outside].head(4))})")
    coords = coords[~outside]

    coords[["population", "median_income"]] = coords[["population", "median_income"]].round(0).astype("Int64")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    coords.to_csv(OUT, index=False)
    print(f"Saved {len(coords):,} suburb centroids -> {OUT.relative_to(ROOT).as_posix()}")

    # Coverage against the tables the map joins to
    for name, col in [("suburb_growth", "suburb"), ("suburb_value_gap", "suburb"), ("suburb_postcode", "suburb")]:
        t = pd.read_csv(ROOT / f"data/exports/{name}.csv")
        hit = t[col].isin(set(coords.suburb)).sum()
        print(f"  {name}: {hit:,} of {len(t):,} rows have a centroid")


if __name__ == "__main__":
    main()
