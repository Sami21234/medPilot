"""
Loads the trained model ONCE at import time (not per-request) and exposes a
simple predict(symptoms) function. Handles bad input gracefully rather than crashing the app.
"""
import joblib       # used for loading the trained machine learning model
import numpy as np       # used for numerical operations and array manipulations
import pandas as pd       # used for data manipulation and analysis
from pathlib import Path       # used for handling file paths

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"       # define the directory where the trained model is stored

_model = joblib.load(MODELS_DIR / "best_model.joblib")       # load the trained machine learning model from the specified file
_label_encoder = joblib.load(MODELS_DIR / "disease_label_encoder.joblib")       # load the label encoder from the specified file
_feature_columns = joblib.load(MODELS_DIR / "feature_columns.joblib")       # load the feature columns from the specified file

_scaler = None       # initialize the scaler variable to None
_scaler_path = MODELS_DIR / "scaler.joblib"       # define the path to the scaler file
if _scaler_path.exists():       # check if the scaler file exists
    _scaler = joblib.load(_scaler_path)       # load the scaler from the specified file

_severity = pd.read_csv(Path(__file__).resolve().parent.parent / "data/processed/severity_clean.csv")       # load the severity data from the specified CSV file
_severity_map = dict(zip(_severity["Symptom"], _severity["weight"]))       # create a dictionary mapping symptoms to their corresponding severity weights
_symptom_only_cols = [col for col in _feature_columns if col not in ("symptom_count", "severity_score")]       # create a list of feature columns that only include symptoms, excluding symptom count and severity score

class InvalidSymptomError(Exception):       # define a custom exception class for invalid symptoms
    pass

def get_valid_symptoms() -> list[str]:       # define a function that returns a list of valid symptoms
    """Returns the list of valid symptom names that the model was trained on."""
    return _symptom_only_cols       # return the list of valid symptom columns

def predict(symptom_names: list[str]) -> dict:       # define a function that takes a list of symptom names and returns a dictionary with the predicted disease and probability
    """
    Takes a list of symptom names (e.g. ["itching", "skin_rash"]), returns
    the predicted disease name and a confidence score. Raises
    InvalidSymptomError with a clear message if given unrecognized symptoms
    or an empty list -- caller (the Flask route) turns this into a proper
    HTTP error response.
    """
    if not symptom_names:       # check if the list of symptom names is empty
        raise InvalidSymptomError("At least one symptom must be provided.")       # raise an InvalidSymptomError if no symptoms are provided

    unknown = [s for s in symptom_names if s not in _symptom_only_cols]       # create a list of unknown symptoms that are not in the valid symptom columns
    if unknown:       # check if there are any unknown symptoms
        raise InvalidSymptomError(f"Unknown symptoms: {', '.join(unknown)}")       # raise an InvalidSymptomError with a message listing the unknown symptoms

    row = {c: 0 for c in _symptom_only_cols}       # create a dictionary with all feature columns initialized to 0
    for s in symptom_names:       # iterate over the list of symptom names
        row[s] = 1       # set the corresponding feature column to 1 for each symptom

    symptom_count = sum(row.values())       # calculate the total number of symptoms provided
    severity_score = sum(_severity_map.get(s, 0) * row[s] for s in _symptom_only_cols)       # calculate the severity score based on the severity weights of the symptoms

    feature_row = [row[c] for c in _symptom_only_cols] + [symptom_count, severity_score]      # create a list representing the feature row for the model input
    X = pd.DataFrame([feature_row], columns=_feature_columns)       # create a DataFrame from the feature row with the appropriate column names

    if _scaler is not None:       # check if a scaler is loaded
        X = _scaler.transform(X)       # scale the input features using the loaded scaler

    pred_encoded = _model.predict(X)[0]       # make a prediction using the trained model and get the encoded predicted label
    disease_name = _label_encoder.inverse_transform([pred_encoded])[0]       # decode the predicted label to get the disease name

    confidence = None       # initialize the confidence variable to None
    if hasattr(_model, "predict_proba"):       # check if the model has the predict_proba method
        proba = _model.predict_proba(X)[0]      # get the predicted probabilities for each class
        confidence = float(np.max(proba))       # get the confidence score for the predicted class

    return {"disease": disease_name, "confidence": confidence}       # return a dictionary containing the predicted disease name and confidence score
