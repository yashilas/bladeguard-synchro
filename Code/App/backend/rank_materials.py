# =============================================================================
# Material Shortlist Ranker — tuned for Final.csv (MatWeb export)
#
# Ranks materials by three criteria:
#   ✓ Low density        (lighter is better)
#   ✓ High elongation    (more stretchy / ductile is better)
#   ✓ High tensile strength (stronger is better)
#
# All three are combined into one Score between 0 (worst) and 1 (best).
# =============================================================================

from pathlib import Path

import pandas as pd   # for reading and working with tabular data
import re             # for pulling numbers out of text like "5300 - 8000 psi"
import unicodedata

# -----------------------------------------------------------------------------
# CONFIGURATION  ← only change things here
# -----------------------------------------------------------------------------

data_dir = Path(__file__).parent.parent.parent   / "data" 
INPUT_FILE  = data_dir / "Final.csv"     # your MatWeb CSV file
OUTPUT_FILE = data_dir / "ranked_materials.csv"
OUTPUT_FILE_CLEAN = data_dir / "ranked_materials_clean.csv"
TOP_N       = 200             # how many materials to show in the printed table

# Column names as they appear in the CSV
COL_NAME       = "MaterialName"
COL_FAMILY     = "Family"
COL_DENSITY    = "density"
COL_STRENGTH   = "tensile strength"
COL_ELONGATION = "elongation at break"


# =============================================================================
# STEP 1 — LOAD THE FILE
# MatWeb exports with non-standard characters, so we use encoding='latin-1'
# =============================================================================

print(f"\nReading: {INPUT_FILE}")
df = pd.read_csv(INPUT_FILE, encoding="latin-1")
print(f"  {len(df)} rows, {len(df.columns)} columns found.\n")


# =============================================================================
# STEP 2 — HELPER FUNCTIONS
# MatWeb stores values like "5300 - 8000 psi" (a range with units).
# These functions extract the midpoint and convert to standard units.
# =============================================================================

def midpoint(text):
    """
    Pull all numbers out of a string and return their average.
    Example: "5300 - 8000 psi"  →  [5300, 8000]  →  6650.0
    Example: "700%"             →  [700]          →  700.0
    Returns None if no numbers found.
    """
    numbers = re.findall(r"[\d.]+", str(text))
    if not numbers:
        return None
    values = [float(n) for n in numbers]
    return sum(values) / len(values)


def parse_density(text):
    """
    Convert density to g/cc.
    Handles two units found in this file:
      - g/cc  → kept as-is
      - lb/in³ → multiplied by 27.6799 to get g/cc
    """
    val = midpoint(text)
    if val is None:
        return None
    if "lb/in" in str(text):
        return val * 27.6799   # 1 lb/in³ = 27.6799 g/cc
    return val                 # already in g/cc


def parse_strength(text):
    """
    Convert tensile strength to MPa.
    Handles:
      - MPa  → kept as-is
      - psi  → multiplied by 0.00689476 to get MPa
    Skips rows that accidentally contain density values or 'Compressive'.
    """
    s = str(text)
    if "g/cc" in s or "Compressive" in s:
        return None            # bad data in this cell — skip it
    val = midpoint(text)
    if val is None:
        return None
    if "psi" in s:
        return val * 0.00689476   # 1 psi = 0.00689476 MPa
    return val                    # already in MPa


def parse_elongation(text):
    """
    Extract the elongation percentage (just grab the number).
    Example: "370 - 470 %"  →  420.0
    Example: "700%"         →  700.0
    """
    return midpoint(text)


# =============================================================================
# STEP 3 — APPLY THE PARSERS
# Creates three new columns with clean, comparable numbers.
# =============================================================================

df["density_gcc"]    = df[COL_DENSITY].apply(parse_density)
df["strength_mpa"]   = df[COL_STRENGTH].apply(parse_strength)
df["elongation_pct"] = df[COL_ELONGATION].apply(parse_elongation)


# =============================================================================
# STEP 4 — REMOVE ROWS WITH MISSING VALUES
# If any of the three key properties is missing, we can't rank that material.
# =============================================================================

rows_before = len(df)
df = df.dropna(subset=["density_gcc", "strength_mpa", "elongation_pct"]).copy()
rows_after = len(df)

print(f"Rows kept after cleaning: {rows_after} / {rows_before}")
print(f"  ({rows_before - rows_after} rows dropped — missing at least one property)\n")

if rows_after == 0:
    raise ValueError("No data remains after cleaning. Check your column names.")


# =============================================================================
# STEP 5 — SCORE EACH MATERIAL
#
# We use "min-max normalisation" to put all three properties on a 0–1 scale:
#   normalised = (value − min) / (max − min)
#
#   Score of 1.0 = best material in the dataset for that property
#   Score of 0.0 = worst material in the dataset for that property
#
# For density we FLIP the score (1 − normalised) because LOWER is better.
# Then we average the three scores into one overall Score.
# =============================================================================

def normalise(series):
    """Scale a column to 0–1 range."""
    lo, hi = series.min(), series.max()
    if hi == lo:
        return series * 0 + 0.5   # all values identical → neutral score
    return (series - lo) / (hi - lo)


density_score    = 1 - normalise(df["density_gcc"])    # low density  → high score
elongation_score =     normalise(df["elongation_pct"]) # high elongation → high score
strength_score   =     normalise(df["strength_mpa"])   # high strength → high score

# Equal weighting (1/3 each). To change weights, adjust the numbers that
# multiply each score and divide by their sum. For example, to double the
# weight of strength:
#   Score = (1*density_score + 1*elongation_score + 2*strength_score) / 4
df["Score"] = (density_score + elongation_score + strength_score) / 3


# =============================================================================
# STEP 6 — SORT AND DISPLAY TOP RESULTS
# =============================================================================

df_ranked = df.sort_values("Score", ascending=False).reset_index(drop=True)
df_ranked.index += 1   # start at rank 1 instead of 0

print(f"{'='*95}")
print(f"  TOP {TOP_N} MATERIALS  (Score = 0 worst → 1 best, equal weighting)")
print(f"{'='*95}")

header = f"{'Rank':<5} {'Material':<45} {'Density':>10} {'Elongation':>12} {'Strength':>12} {'Score':>7}"
print(header)
print("-" * len(header))

for rank, row in df_ranked.head(TOP_N).iterrows():
    name = str(row[COL_NAME])[:44]
    print(
        f"{rank:<5} {name:<45} "
        f"{row['density_gcc']:>8.3f}g/cc "
        f"{row['elongation_pct']:>10.1f}% "
        f"{row['strength_mpa']:>9.1f}MPa "
        f"{row['Score']:>7.4f}"
    )


# =============================================================================
# STEP 7 — SAVE FULL RANKED LIST AND CLEAN FORMATTED CSVS
# =============================================================================

raw_cols = [
    "No",
    COL_NAME,
    COL_FAMILY,
    COL_DENSITY,
    COL_STRENGTH,
    COL_ELONGATION,
    "modulus if available",
    "tear or impact related values if available,",
    "minimum service temperature if available",
    "form availability: film, fiber, sheet, coating, fabric",
    "first impression: impact layer candidate, cut layer candidate, or hybrid layer candidate",
    "Notes",
]


def clean_text(value):
    if isinstance(value, str):
        text = value.replace("\xa0", " ")
        text = text.replace("\u2019", "'")
        text = text.replace("\u2013", "-")
        text = text.replace("\u2014", "-")
        text = text.replace("\u2212", "-")
        text = text.replace("°", "")
        text = unicodedata.normalize("NFKC", text)
        return text.strip()
    return value

output_full = df_ranked[raw_cols + ["density_gcc", "elongation_pct", "strength_mpa", "Score"]].copy()
output_full[raw_cols] = output_full[raw_cols].map(clean_text)
output_full.to_csv(OUTPUT_FILE, index_label="Rank", encoding="utf-8-sig")
print(f"\nFull ranked list saved to: {OUTPUT_FILE}")

output_clean = output_full.copy()
output_clean["Density"] = output_clean["density_gcc"].map(lambda v: f"{v:.3f}g/cc")
output_clean["Elongation"] = output_clean["elongation_pct"].map(lambda v: f"{v:.1f}%")
output_clean["Strength"] = output_clean["strength_mpa"].map(lambda v: f"{v:.1f}MPa")
output_clean["Score"] = output_clean["Score"].map(lambda v: f"{v:.4f}")

output_clean = output_clean[
    raw_cols + ["density_gcc", "Density", "elongation_pct", "Elongation", "strength_mpa", "Strength", "Score"]
]

output_clean.to_csv(OUTPUT_FILE_CLEAN, index_label="Rank", encoding="utf-8-sig")
print(f"Clean ranked list saved to: {OUTPUT_FILE_CLEAN}")
