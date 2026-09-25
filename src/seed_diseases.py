"""
Loads the cleaned reference data (description, medications, diets,
precautions, workout) into the database. Without this, a validated Case
has no actual recommendation content to show the patient. Run once:
python -m src.seed_diseases
"""

import ast
import pandas as pd
from app import create_app
from src.models import db, Disease, Medication, Diet, Precaution, Workout

app = create_app()

with app.app_context():
    desc = pd.read_csv("data/processed/description_clean.csv")
    meds = pd.read_csv("data/processed/medications_clean.csv")
    diets = pd.read_csv("data/processed/diets_clean.csv")
    precau = pd.read_csv("data/processed/precautions_clean.csv")
    workout = pd.read_csv("data/processed/workout_clean.csv")

    def get_or_create_disease(name, description = None):
        d = Disease.query.filter_by(name = name).first()
        if d is None:
            d = Disease(name = name, description = description)
            db.session.add(d)
            db.session.flush()
        elif description and not d.description:
            d.description = description
        return d

    for _, row in desc.iterrows():
        get_or_create_disease(row["Disease"], row["Description"])

    def parse_list_field(value):
        if pd.isna(value):
            return []
        try:
            parsed = ast.literal_eval(value)
            return parsed if isinstance(parsed, list) else [str(parsed)]
        except (ValueError, SyntaxError):
            return [str(value)]

    for _, row in meds.iterrows():
        d = get_or_create_disease(row["Disease"])
        for item in parse_list_field(row["Medication"]):
            db.session.add(Medication(disease_id=d.id, content=item))

    for _, row in diets.iterrows():
        d = get_or_create_disease(row["Disease"])
        for item in parse_list_field(row["Diet"]):
            db.session.add(Diet(disease_id=d.id, content=item))

    precaution_cols = [c for c in precau.columns if c.lower().startswith("precaution")]
    for _, row in precau.iterrows():
        d = get_or_create_disease(row["Disease"])
        for col in precaution_cols:
            if pd.notna(row[col]) and str(row[col]).strip():
                db.session.add(Precaution(disease_id=d.id, content=row[col]))

    for _, row in workout.iterrows():
        d = get_or_create_disease(row["disease"])
        db.session.add(Workout(disease_id=d.id, content=row["workout"]))

    db.session.commit()
    print(f"Seeded {Disease.query.count()} diseases with full reference data.")