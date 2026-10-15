"""Repeat-sales price index (Bailey-Muth-Nourse), the method behind Case-Shiller / CoreLogic-style indices.

Idea: compare the *same property* sold twice. Its bedrooms, land and location don't change between the two
sales, so the price change is pure market movement. That removes the "what sold" (composition) bias of medians.

    log(P2 / P1) = beta[t2] - beta[t1] + error      ->  index[t] = exp(beta[t]),  beta[base] = 0
"""
import numpy as np
import pandas as pd

# Pair filters: guard against renovations, knock-down-rebuilds, subdivisions and data errors
MIN_HOLD_DAYS = 180
MAX_ANNUAL_LOG_RETURN = 0.40     # > ~49% p.a. is almost certainly not the same dwelling
MIN_ANNUAL_LOG_RETURN = -0.30    # < ~-26% p.a. likewise
MAX_LAND_CHANGE = 0.05           # houses: land area must match within 5% (no subdivision)
# Property IDs are issued roughly in sequence; IDs above this first appear from ~2011 (new lots / strata plans).
NEW_PROPERTY_ID_MIN = 3_400_000


def build_pairs(sales: pd.DataFrame) -> tuple[pd.DataFrame, list[tuple[str, int]]]:
    """Turn sales into consecutive (first sale, next sale) pairs of the same dwelling.

    A dwelling is property_id for houses, property_id + strata_lot_number for strata.
    Returns the pairs plus a (step, rows) funnel for reporting.
    """
    s = sales.dropna(subset=["property_id"]).copy()
    s["lot"] = s["strata_lot_number"].fillna(-1)
    s = s.sort_values(["property_id", "lot", "contract_date"])
    key = ["property_id", "lot"]

    nxt = s.groupby(key).shift(-1)
    pairs = pd.DataFrame({
        "property_id": s["property_id"], "lot": s["lot"], "suburb": s["suburb"],
        "post_code": s["post_code"], "segment": s["segment"],
        "date1": s["contract_date"], "price1": s["purchase_price"], "land1": s["land_sqm"],
        "date2": nxt["contract_date"], "price2": nxt["purchase_price"], "land2": nxt["land_sqm"],
        "segment2": nxt["segment"], "first_sale": s["dwelling_first_sale"],
    }).dropna(subset=["date2"])
    # First sale of a newly created dwelling = developer / off-the-plan / vacant-lot sale, not an established home
    pairs["new_build_first"] = (pairs["property_id"] >= NEW_PROPERTY_ID_MIN) & (pairs["date1"] <= pairs["first_sale"])
    funnel = [("Consecutive sale pairs", len(pairs))]

    pairs = pairs[pairs["segment"] == pairs["segment2"]]
    funnel.append(("Same dwelling type at both sales", len(pairs)))

    pairs["years"] = (pairs["date2"] - pairs["date1"]).dt.days / 365.25
    pairs = pairs[pairs["years"] * 365.25 >= MIN_HOLD_DAYS]
    funnel.append((f"Held at least {MIN_HOLD_DAYS} days (drops flips / re-recorded sales)", len(pairs)))

    land_ok = (pairs["land1"].isna() | pairs["land2"].isna()
               | ((pairs["land2"] / pairs["land1"] - 1).abs() <= MAX_LAND_CHANGE))
    pairs = pairs[land_ok]
    funnel.append((f"Land area unchanged (within {MAX_LAND_CHANGE:.0%})", len(pairs)))

    pairs["log_ret"] = np.log(pairs["price2"] / pairs["price1"])
    ann = pairs["log_ret"] / pairs["years"]
    pairs = pairs[ann.between(MIN_ANNUAL_LOG_RETURN, MAX_ANNUAL_LOG_RETURN)]
    funnel.append(("Plausible annual return (drops renovations / errors)", len(pairs)))

    return pairs.drop(columns=["segment2", "first_sale"]).reset_index(drop=True), funnel


def exclude_new_builds(pairs: pd.DataFrame) -> pd.DataFrame:
    """Drop pairs whose first sale is a new dwelling's first-ever sale (it measures construction, not market growth)."""
    return pairs[~pairs["new_build_first"]]


def _design(pairs: pd.DataFrame, freq: str):
    p1 = pairs["date1"].dt.to_period(freq)
    p2 = pairs["date2"].dt.to_period(freq)
    periods = pd.period_range(min(p1.min(), p2.min()), max(p1.max(), p2.max()), freq=freq)
    pos = {p: i for i, p in enumerate(periods)}
    i1, i2 = p1.map(pos).to_numpy(), p2.map(pos).to_numpy()
    keep = i1 != i2                              # both sales in one period carry no information
    n = keep.sum()
    X = np.zeros((n, len(periods)))
    X[np.arange(n), i2[keep]] += 1
    X[np.arange(n), i1[keep]] -= 1
    return X[:, 1:], pairs["log_ret"].to_numpy()[keep], periods, keep   # drop base period -> beta[base] = 0


def _ols(X, y):
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ (X.T @ y)
    resid = y - X @ beta
    sigma2 = resid @ resid / max(len(y) - X.shape[1], 1)
    return beta, sigma2 * XtX_inv


def fit_index(pairs: pd.DataFrame, freq: str = "Y") -> pd.DataFrame:
    """Fit a BMN repeat-sales index. freq 'Y' (annual) or 'Q' (quarterly).

    Returns a frame indexed by period with: index (base period = 100), log_index, se (std error of log_index).
    The full covariance matrix of log_index is in `.attrs["cov"]`.
    """
    X, y, periods, _ = _design(pairs, freq)
    beta, cov = _ols(X, y)
    k = len(periods)
    full_cov = np.zeros((k, k))
    full_cov[1:, 1:] = cov
    log_index = np.concatenate([[0.0], beta])
    out = pd.DataFrame({"index": 100 * np.exp(log_index), "log_index": log_index,
                        "se": np.sqrt(np.diag(full_cov)), "n_pairs": len(y)}, index=periods)
    out.attrs["cov"] = full_cov
    return out


def effect_of_flag(pairs: pd.DataFrame, flag: str, freq: str = "Y") -> tuple[float, float]:
    """Average % price difference for pairs where `flag` is True, holding the market index fixed.

    Adds the flag as an extra regressor to the repeat-sales model. Returns (effect %, 95% CI half-width in % pts).
    """
    X, y, _, keep = _design(pairs, freq)
    X = np.column_stack([X, pairs[flag].to_numpy()[keep].astype(float)])
    beta, cov = _ols(X, y)
    g, se = beta[-1], np.sqrt(cov[-1, -1])
    return np.expm1(g) * 100, (np.expm1(g + 1.96 * se) - np.expm1(g - 1.96 * se)) / 2 * 100


def signal_volatility(ix: pd.DataFrame) -> float:
    """Std dev of annual log changes with estimation noise removed (floored at 0).

    For thin suburbs, much of the year-to-year wobble in an estimated index is sampling noise. Using the
    fitted covariance, noise variance of each change is V[t,t] + V[t-1,t-1] - 2 V[t,t-1].
    """
    li, V = ix["log_index"].to_numpy(), ix.attrs["cov"]
    d = np.diff(li)
    noise = np.array([V[t, t] + V[t - 1, t - 1] - 2 * V[t, t - 1] for t in range(1, len(li))])
    return float(np.sqrt(max(d.var(ddof=1) - noise.mean(), 0.0)))


def shrink(estimate: pd.Series, se: pd.Series) -> tuple[pd.Series, float]:
    """Empirical-Bayes shrinkage toward the group mean: noisy estimates are pulled in more than precise ones.

    tau^2 (true between-suburb variance) = observed variance - average sampling variance.
    Returns (shrunk estimates, tau).
    """
    w_mean = np.average(estimate, weights=1 / se**2)
    tau2 = max(estimate.var(ddof=1) - (se**2).mean(), 1e-12)
    weight = tau2 / (tau2 + se**2)
    return w_mean + weight * (estimate - w_mean), float(np.sqrt(tau2))
