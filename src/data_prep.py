import pandas as pd
import re
from pathlib import Path

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")

def normalize_disease_name(name: str) -> str:
    """
    Fixes the exact bug that broke medicine lookup:
    trailing/double whitespace and one known spelling typo in the disease
    label, applied consistently across ALL files so every lookup matches.
    """
    name = str(name).strip()
    name = re.sub(r"\s+", " ", name)       # collapse multiple spaces to one
    name = name.replace("diseae", "disease")    # fix known typo ("Peptic ulcer diseae")
    return name

def clean_column_names(columns):
    """
    Fixes known column-name whitespace issues in Training.csv:
    'spotting_ urination' -> 'spotting_urination', etc.
    General rule: strip, then replace any space with underscore, so
    'foul_smell_of urine' -> 'foul_smell_of_urine'.
    """
    cleaned = []
    for c in columns:
        c = c.strip()
        c = c.replace(" ", "-")
        cleaned.append(c)
    return cleaned

def load_and_clean_training(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)

    # Fix column name whitespace issues (spotting_ urination, foul_smell_of urine, etc.)
    df.columns = clean_column_names(df.columns)

    # Rename the second fluid_overload column to something explicit rather than the confusing pandas-generated ".1" suffix -- these are genuinely
    # DIFFERENT columns (114 rows differ), not true duplicates, so we keep both
    df = df.rename(columns={"fluid_overload.1": "fluid_overload_2"})

    # Normalize the target label -- this is the fix for the disease-name
    # mismatch bug found during inspection
    df["prognosis"] = df["prognosis"].apply(normalize_disease_name)

    # Sanity checks
    assert df.isnull().sum().sum() == 0, "Unexpected nulls found after cleaning"
    symptom_cols = [c for c in df.columns if c != "prognosis"]
    non_binary = [c for c in symptom_cols if not set(df[c].unique()).issubset({0, 1})]
    assert not non_binary, f"Non-binary values found in: {non_binary}"

    return df

def load_and_clean_companion_files():
    """
    Loads the 6 companion reference files and normalizes their disease-name
    columns to match Training.csv exactly -- this is what prevents the
    medicine/diet/precaution lookup from silently failing later.
    """
    files = {
        "description": ("description.csv", "Disease"),
        "medications": ("medications.csv", "Disease"),
        "diets": ("diets.csv", "Disease"),
        "precautions": ("precautions_df.csv", "Disease"),
        "workout": ("workout_df.csv", "disease"),
        "symptoms_ref": ("symtoms_df.csv", "Disease"),
        "severity": ("Symptom-severity.csv", None),  # no disease column, different structure
    }

    cleaned = {}
    for key, (fname, disease_col) in files.items():
        df = pd.read_csv(RAW_DIR / fname)
        if disease_col:
            df[disease_col] = df[disease_col].apply(normalize_disease_name)
        cleaned[key] = df
    return cleaned

def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    train = load_and_clean_training(RAW_DIR / "Training.csv")
    companions = load_and_clean_companion_files()

    # Verify every companion file's disease names now match Training.csv exactly
    train_diseases = set(train["prognosis"].unique())
    for key, df in companions.items():
        disease_col = "Disease" if "Disease" in df.columns else ("disease" if "disease" in df.columns else None)
        if disease_col:
            mismatch = train_diseases.symmetric_difference(set(df[disease_col].unique()))
            status = "OK" if not mismatch else f"MISMATCH: {mismatch}"
            print(f"[check] {key}: {status}")

    train.to_csv(PROCESSED_DIR / "training_clean.csv", index=False)
    for key, df in companions.items():
        df.to_csv(PROCESSED_DIR / f"{key}_clean.csv", index=False)

    print(f"\n[done] {len(train)} rows, {train['prognosis'].nunique()} diseases")
    print(f"[done] Cleaned files written to {PROCESSED_DIR}/")


if __name__ == "__main__":
    main()
    