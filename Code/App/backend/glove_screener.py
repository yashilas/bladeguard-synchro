# =============================================================================
# Glove Material Weighted Screener
#
# Scores each candidate material across four glove-relevant criteria:
#
#   Criterion                    Weight   Key properties used
#   ─────────────────────────────────────────────────────────
#   Flexibility                  0.30     Elongation at break, modulus
#   Cut resistance potential     0.25     Tensile strength, modulus
#   Impact protection potential  0.20     Impact/tear values, tensile strength
#   Low density / light weight   0.10     Density
#   Low temperature suitability  0.15     Minimum service temperature
#
# Each criterion is scored 0–1. The weighted total is also 0–1.
# =============================================================================

from pathlib import Path

import pandas as pd
import re

# ── CONFIGURATION ─────────────────────────────────────────────────────────────

data_dir = Path(__file__).parent.parent.parent   / "data" 
INPUT_FILE  = data_dir / "Final.csv"
OUTPUT_FILE = data_dir / "glove_screener_results.csv"
TOP_N       = 15   # rows to print in the summary table

# Minimum number of real (non-null) property values a material must have
# to be included in the ranking. Raises this to be more strict.
MIN_DATA_FIELDS = 2

# Weights — must sum to 1.0
W_FLEX     = 0.30   # flexibility
W_CUT      = 0.25   # cut resistance potential
W_IMPACT   = 0.20   # impact protection potential
W_DENSITY  = 0.10   # low density / light weight
W_TEMP     = 0.15   # low temperature suitability

# ── LOAD ──────────────────────────────────────────────────────────────────────

print(f"\nReading: {INPUT_FILE}")
df = pd.read_csv(INPUT_FILE, encoding="latin-1")
print(f"  {len(df)} rows loaded.\n")

# Drop rows with no material name (placeholder / blank rows in the CSV)
df = df[df["MaterialName"].notna()].copy()

# ── UNIT CONVERSION HELPERS ───────────────────────────────────────────────────

def midpoint(text):
    """
    Pull all numbers (including negatives) from a string and return
    their average. Used to handle ranges like '5300 - 8000 psi'.
    Returns None if no numbers are found.
    """
    nums = re.findall(r"-?\d+\.?\d*", str(text))
    if not nums:
        return None
    vals = [float(n) for n in nums]
    return sum(vals) / len(vals)


def parse_modulus(text):
    """
    Convert elastic modulus to MPa.
    Handles: GPa, Gpa, ksi, MPa.
    Returns None for non-modulus entries.
    """
    s = str(text)
    if pd.isna(text) or s in ("nan", ""):
        return None
    val = midpoint(text)
    if val is None:
        return None
    if "GPa" in s or "Gpa" in s:
        return val * 1000        # 1 GPa = 1000 MPa
    if "ksi" in s:
        return val * 6.89476     # 1 ksi = 6.89476 MPa
    return val                   # already MPa


def parse_strength(text):
    """
    Convert tensile strength to MPa.
    Skips cells that accidentally contain density or 'Compressive Strength'.
    """
    s = str(text)
    if pd.isna(text) or "g/cc" in s or "Compressive" in s:
        return None
    val = midpoint(text)
    if val is None:
        return None
    if "psi" in s:
        return val * 0.00689476  # 1 psi = 0.00689476 MPa
    return val                   # already MPa


def parse_elongation(text):
    """Extract elongation percentage as a plain number."""
    return midpoint(text)


def parse_density(text):
    """
    Convert density to g/cc.
    Handles g/cc and lb/in³ values that appear in the material export.
    """
    s = str(text)
    if pd.isna(text) or s in ("nan", ""):
        return None
    val = midpoint(text)
    if val is None:
        return None
    if "lb/in" in s:
        return val * 27.6799   # 1 lb/in³ = 27.6799 g/cc
    return val


def parse_impact(text):
    """
    Convert impact/tear values to MPa where the unit is clear.
    Skips: kN/m (tear, different units), bare unitless numbers (J/m impact
    values from Nylon rows), and anything that looks like heat capacity.
    """
    s = str(text)
    if pd.isna(text) or "kN/m" in s or "J/g" in s:
        return None
    # Unitless entries (e.g. "23.0 - 14000") are J/m Izod/Charpy impact —
    # no clean conversion to MPa, so skip them.
    if re.fullmatch(r"[\d\s.\-]+", s.strip()):
        return None
    val = midpoint(text)
    if val is None:
        return None
    if "GPa" in s:
        return val * 1000
    if "MPa" in s or "Mpa" in s:
        return val
    return None


def parse_min_temp(text):
    """
    Extract the lowest service temperature in °C.
    Skips heat-capacity cells (J/g-°C) and positive temperatures
    (which indicate heat rating, not cold rating).
    Returns None when no usable cold-temperature rating exists.
    """
    s = str(text)
    if pd.isna(text) or "J/g" in s:
        return None
    if "°C" not in s and "øC" not in s:
        return None
    nums = re.findall(r"-?\d+\.?\d*", s)
    if not nums:
        return None
    lowest = min(float(n) for n in nums)
    # Only count it if it's a sub-zero temperature (cold rating)
    return lowest if lowest < 0 else None


# ── PARSE ALL COLUMNS ─────────────────────────────────────────────────────────

df["elongation_pct"] = df["elongation at break"].apply(parse_elongation)
df["modulus_mpa"]    = df["modulus if available"].apply(parse_modulus)
df["strength_mpa"]   = df["tensile strength"].apply(parse_strength)
df["impact_mpa"]     = df["tear or impact related values if available,"].apply(parse_impact)
df["density_gcc"]    = df["density"].apply(parse_density)
df["min_temp_c"]     = df["minimum service temperature if available"].apply(parse_min_temp)

# ── MINIMUM DATA FILTER ───────────────────────────────────────────────────────
# Count how many of the five parsed numeric fields each material has.
# Materials with fewer than MIN_DATA_FIELDS real values are excluded —
# they would otherwise inherit median scores and rank misleadingly.

data_cols = ["elongation_pct", "modulus_mpa", "strength_mpa", "impact_mpa", "density_gcc", "min_temp_c"]
df["data_count"] = df[data_cols].notna().sum(axis=1)

before = len(df)
df = df[df["data_count"] >= MIN_DATA_FIELDS].copy()
after  = len(df)

print(f"Materials with enough data to rank: {after} / {before}")
print(f"  ({before - after} excluded — fewer than {MIN_DATA_FIELDS} measurable properties)\n")

# ── NORMALISATION ─────────────────────────────────────────────────────────────

def norm(series):
    """
    Min-max normalise a series to 0–1.
    Score 1.0 = best value in the dataset.
    Score 0.0 = worst value in the dataset.
    """
    lo, hi = series.min(), series.max()
    if hi == lo:
        return series * 0 + 0.5   # all identical → neutral
    return (series - lo) / (hi - lo)


# ── CRITERION 1: FLEXIBILITY (weight 0.35) ────────────────────────────────────
# High elongation = stretchy = flexible  →  higher score is better
# Low modulus     = soft/pliable        →  lower modulus = higher score (inverted)
# When both values exist, average them. When only one exists, use it alone.

elong_filled = df["elongation_pct"].fillna(df["elongation_pct"].median())
mod_filled   = df["modulus_mpa"].fillna(df["modulus_mpa"].median())

elong_norm   = norm(elong_filled)
mod_norm_inv = 1 - norm(mod_filled)   # inverted: low modulus = flexible = good

has_e = df["elongation_pct"].notna()
has_m = df["modulus_mpa"].notna()

# Both available → average; only one → use it; neither → 0.5 (neutral)
flex_score = ((elong_norm + mod_norm_inv) / 2).where(has_e & has_m,
              elong_norm.where(has_e,
              mod_norm_inv.where(has_m, 0.5)))

df["flex_score"] = flex_score


# ── CRITERION 2: CUT RESISTANCE POTENTIAL (weight 0.30) ──────────────────────
# High tensile strength = harder to cut through
# High modulus = stiffer = resists blade penetration
# Both contribute; average when both present.

str_filled = df["strength_mpa"].fillna(df["strength_mpa"].median())
str_norm   = norm(str_filled)
mod_norm   = norm(mod_filled)   # high modulus = good for cut resistance

has_s = df["strength_mpa"].notna()

cut_score = ((str_norm + mod_norm) / 2).where(has_s & has_m,
             str_norm.where(has_s,
             mod_norm.where(has_m, 0.5)))

df["cut_score"] = cut_score


# ── CRITERION 3: IMPACT PROTECTION POTENTIAL (weight 0.20) ───────────────────
# Direct impact/tear values are used first.
# If unavailable, tensile strength is used as a proxy (higher strength
# materials generally absorb more energy before failure).

impact_combined = df["impact_mpa"].fillna(df["strength_mpa"])
impact_combined = impact_combined.fillna(impact_combined.median())
df["impact_score"] = norm(impact_combined)


# ── CRITERION 4: LOW DENSITY / LIGHT WEIGHT (weight 0.10) ───────────────────
# Lower density means lighter glove layers. Missing density values are treated
# as neutral rather than penalized.

density_series = df["density_gcc"].copy()
density_norm = 1 - norm(density_series.fillna(density_series.median()))
density_score = density_norm.where(density_series.notna(), 0.5)
df["density_score"] = density_score


# ── CRITERION 5: LOW TEMPERATURE SUITABILITY (weight 0.15) ───────────────────
# Lower minimum service temperature = rated for colder environments = better.
# Materials with no low-temperature data receive a conservative neutral score
# of 0.3 (slight penalty for unknown cold performance).

temp_series = df["min_temp_c"].copy()

# Invert: more negative temperature = better cold rating = higher score
temp_score = 1 - norm(temp_series.fillna(0))
temp_score = temp_score.where(temp_series.notna(), 0.30)  # neutral for unknowns

df["temp_score"] = temp_score


# ── WEIGHTED TOTAL ────────────────────────────────────────────────────────────

df["Total Score"] = (
    W_FLEX    * df["flex_score"]    +
    W_CUT     * df["cut_score"]     +
    W_IMPACT  * df["impact_score"]  +
    W_DENSITY * df["density_score"] +
    W_TEMP    * df["temp_score"]
)

df_ranked = df.sort_values("Total Score", ascending=False).reset_index(drop=True)
df_ranked.index += 1


# ── PRINT RESULTS ─────────────────────────────────────────────────────────────

print(f"{'='*110}")
print(f"  TOP {TOP_N} GLOVE MATERIAL CANDIDATES")
print(f"  Weights: Flexibility {W_FLEX:.0%} | Cut Resistance {W_CUT:.0%} | "
      f"Impact Protection {W_IMPACT:.0%} | Density {W_DENSITY:.0%} | "
      f"Low Temp Suitability {W_TEMP:.0%}")
print(f"{'='*110}")

header = (f"{'Rank':<5} {'Material':<40} {'Family':<26} "
          f"{'Flex':>6} {'Cut':>6} {'Impact':>8} {'Den':>6} {'Temp':>6} {'TOTAL':>7}")
print(header)
print("-" * len(header))

for rank, row in df_ranked.head(TOP_N).iterrows():
    name   = str(row["MaterialName"])[:39]
    family = str(row["Family"])[:25] if pd.notna(row["Family"]) else "—"
    print(
        f"{rank:<5} {name:<40} {family:<26} "
        f"{row['flex_score']:>6.3f} "
        f"{row['cut_score']:>6.3f} "
        f"{row['impact_score']:>8.3f} "
        f"{row['density_score']:>6.3f} "
        f"{row['temp_score']:>6.3f} "
        f"{row['Total Score']:>7.4f}"
    )

print()
print("  Score legend: 0.000 = worst in dataset, 1.000 = best in dataset")


# ── SAVE FULL RESULTS ─────────────────────────────────────────────────────────

out = df_ranked[[
    "MaterialName", "Family", "density_gcc",
    "elongation_pct", "modulus_mpa", "strength_mpa", "impact_mpa", "min_temp_c",
    "flex_score", "cut_score", "impact_score", "density_score", "temp_score", "Total Score", "data_count"
]].rename(columns={
    "MaterialName":   "Material",
    "Family":         "Family",
    "density_gcc":    "Density (g/cc)",
    "elongation_pct": "Elongation (%)",
    "modulus_mpa":    "Modulus (MPa)",
    "strength_mpa":   "Tensile Strength (MPa)",
    "impact_mpa":     "Impact/Tear (MPa)",
    "density_score":  "Density Score",
    "min_temp_c":     "Min Service Temp (°C)",
    "flex_score":     "Flexibility Score",
    "cut_score":      "Cut Resistance Score",
    "impact_score":   "Impact Protection Score",
    "temp_score":     "Low Temp Score",
    "Total Score":    "Total Score (weighted)",
    "data_count":     "# Data Fields Available",
})

out.to_csv(OUTPUT_FILE, index_label="Rank")
print(f"\nFull results saved to: {OUTPUT_FILE}")
