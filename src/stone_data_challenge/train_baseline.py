
import json

import duckdb
import joblib
import numpy as np
import pandas as pd

from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from stone_data_challenge.config import DATA_DIR, REPORTS_DIR


ML_DIR = DATA_DIR / "ml"
MODEL_DIR = DATA_DIR / "models"
REPORT_PATH = REPORTS_DIR / "baseline_metrics.json"

TARGET = "target_pagamento_7d"

FEATURES = [
    "prazo",
    "vlr_desembolsado",
    "perc_retencao",
    "campanhas_7d",
    "campanhas_30d",
    "dias_com_acionamento_30d",
]


def load_split(name):
    path = ML_DIR / f"{name}.parquet"

    if not path.exists():
        raise FileNotFoundError(path)

    con = duckdb.connect()

    try:
        frame = con.execute(
            """
            SELECT
                prazo,
                CAST(vlr_desembolsado AS DOUBLE)
                    AS vlr_desembolsado,
                CAST(perc_retencao AS DOUBLE)
                    AS perc_retencao,
                campanhas_7d,
                campanhas_30d,
                dias_com_acionamento_30d,
                target_pagamento_7d
            FROM read_parquet(?)
            """,
            [str(path)],
        ).fetchdf()
    finally:
        con.close()

    if frame.empty:
        raise ValueError(f"Conjunto vazio: {name}")

    X = frame[FEATURES].replace(
        [np.inf, -np.inf],
        np.nan,
    )

    y = frame[TARGET].astype(int)

    if not y.isin([0, 1]).all():
        raise ValueError("Target deve ser binario")

    return X, y


def evaluate(model, X, y):
    probability = model.predict_proba(X)[:, 1]
    prediction = (probability >= 0.5).astype(int)

    metrics = {
        "observacoes": int(len(y)),
        "taxa_positiva": float(y.mean()),
        "roc_auc": None,
        "pr_auc": float(
            average_precision_score(y, probability)
        ),
        "balanced_accuracy": float(
            balanced_accuracy_score(y, prediction)
        ),
        "brier_score": float(
            brier_score_loss(y, probability)
        ),
        "log_loss": float(
            log_loss(y, probability, labels=[0, 1])
        ),
        "probabilidade_media": float(
            probability.mean()
        ),
    }

    if y.nunique() == 2:
        metrics["roc_auc"] = float(
            roc_auc_score(y, probability)
        )

    return metrics


def main():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    print("\nSTONE | BASELINE ML")
    print("=" * 70)

    X_train, y_train = load_split("train")
    X_val, y_val = load_split("validation")
    X_test, y_test = load_split("test")

    models = {
        "dummy": DummyClassifier(
            strategy="prior"
        ),
        "logistic_regression": Pipeline(
            steps=[
                (
                    "imputer",
                    SimpleImputer(
                        strategy="median",
                        keep_empty_features=True,
                    ),
                ),
                (
                    "scaler",
                    StandardScaler(),
                ),
                (
                    "classifier",
                    LogisticRegression(
                        max_iter=1000,
                        random_state=42,
                    ),
                ),
            ]
        ),
    }

    report = {
        "features": FEATURES,
        "models": {},
    }

    for name, model in models.items():
        print(f"\nMODELO: {name}")

        model.fit(X_train, y_train)

        report["models"][name] = {
            "train": evaluate(
                model, X_train, y_train
            ),
            "validation": evaluate(
                model, X_val, y_val
            ),
            "test": evaluate(
                model, X_test, y_test
            ),
        }

        for split in (
            "train",
            "validation",
            "test",
        ):
            print(f"\n{split.upper()}")

            for metric, value in (
                report["models"][name][split].items()
            ):
                if isinstance(value, float):
                    print(f"{metric}: {value:.4f}")
                else:
                    print(f"{metric}: {value}")

        joblib.dump(
            model,
            MODEL_DIR / f"{name}.joblib",
        )

    REPORT_PATH.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(f"\nRelatorio: {REPORT_PATH}")
    print("[OK] Baselines treinados")


if __name__ == "__main__":
    main()
