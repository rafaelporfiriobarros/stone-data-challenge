
import json

import joblib
import numpy as np

from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from stone_data_challenge.config import DATA_DIR, REPORTS_DIR
from stone_data_challenge.train_baseline import load_split


MODEL_DIR = DATA_DIR / "models"
REPORT = REPORTS_DIR / "campaign_ablation.json"

FINANCIAL_FEATURES = [
    "prazo",
    "vlr_desembolsado",
    "perc_retencao",
]

CAMPAIGN_FEATURES = [
    "campanhas_7d",
    "campanhas_30d",
    "dias_com_acionamento_30d",
]

EXPERIMENTS = {
    "financial_only": FINANCIAL_FEATURES,
    "financial_plus_campaigns": (
        FINANCIAL_FEATURES + CAMPAIGN_FEATURES
    ),
}


def build_model():
    return Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="median",
                    keep_empty_features=True,
                ),
            ),
            ("scaler", StandardScaler()),
            (
                "classifier",
                LogisticRegression(
                    max_iter=1000,
                    random_state=42,
                ),
            ),
        ]
    )


def evaluate(model, X, y):
    probabilities = model.predict_proba(X)[:, 1]

    return {
        "observacoes": int(len(y)),
        "taxa_observada": float(y.mean()),
        "probabilidade_media": float(
            probabilities.mean()
        ),
        "roc_auc": float(
            roc_auc_score(y, probabilities)
        ),
        "pr_auc": float(
            average_precision_score(
                y, probabilities
            )
        ),
        "brier_score": float(
            brier_score_loss(
                y, probabilities
            )
        ),
        "log_loss": float(
            log_loss(
                y, probabilities,
                labels=[0, 1],
            )
        ),
    }


def main():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    X_train, y_train = load_split("train")
    X_val, y_val = load_split("validation")

    results = {}

    print("\nSTONE | CAMPAIGN ABLATION")
    print("=" * 70)

    for name, features in EXPERIMENTS.items():
        model = build_model()

        model.fit(
            X_train[features],
            y_train,
        )

        metrics = evaluate(
            model,
            X_val[features],
            y_val,
        )

        results[name] = {
            "features": features,
            "validation": metrics,
        }

        joblib.dump(
            model,
            MODEL_DIR / f"{name}.joblib",
        )

        print(f"\n{name.upper()}")
        for metric, value in metrics.items():
            print(f"{metric}: {value:.4f}")

    financial = results[
        "financial_only"
    ]["validation"]

    combined = results[
        "financial_plus_campaigns"
    ]["validation"]

    differences = {
        metric: float(
            combined[metric] - financial[metric]
        )
        for metric in (
            "roc_auc",
            "pr_auc",
            "brier_score",
            "log_loss",
        )
    }

    results["incremental_effect"] = differences

    REPORT.write_text(
        json.dumps(
            results,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("\nDIFERENCA: COM CAMPANHAS - SEM CAMPANHAS")
    for metric, value in differences.items():
        print(f"{metric}: {value:+.4f}")

    print(f"\nRelatorio: {REPORT}")
    print("[OK] Experimento concluido")


if __name__ == "__main__":
    main()
