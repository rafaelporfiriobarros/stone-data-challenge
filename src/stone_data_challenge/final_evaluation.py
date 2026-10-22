
import json

import duckdb
import joblib
import numpy as np
import pandas as pd

from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)

from stone_data_challenge.config import (
    DATA_DIR,
    REPORTS_DIR,
)

from stone_data_challenge.calibrate_model import logit
from stone_data_challenge.campaign_ablation import (
    EXPERIMENTS,
)


TEST_PATH = DATA_DIR / "ml" / "test.parquet"

BASE_MODEL_PATH = (
    DATA_DIR
    / "models"
    / "financial_plus_campaigns.joblib"
)

CALIBRATOR_PATH = (
    DATA_DIR
    / "models"
    / "campaign_calibrator.joblib"
)

OUTPUT = REPORTS_DIR / "final_evaluation"

FEATURES = EXPERIMENTS[
    "financial_plus_campaigns"
]


def load_test():
    con = duckdb.connect()

    try:
        df = con.execute(
            """
            SELECT
                contrato_id,
                data_observacao,
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
            ORDER BY
                data_observacao,
                contrato_id
            """,
            [str(TEST_PATH)],
        ).fetchdf()
    finally:
        con.close()

    if df.empty:
        raise ValueError("Conjunto de teste vazio")

    if df.duplicated(
        ["contrato_id", "data_observacao"]
    ).any():
        raise ValueError(
            "Chaves duplicadas no conjunto de teste"
        )

    return df


def evaluate(y, probabilities):
    predictions = (
        probabilities >= 0.5
    ).astype(int)

    return {
        "observacoes": int(len(y)),
        "taxa_observada": float(np.mean(y)),
        "probabilidade_media": float(
            np.mean(probabilities)
        ),
        "roc_auc": float(
            roc_auc_score(y, probabilities)
        ),
        "pr_auc": float(
            average_precision_score(
                y, probabilities
            )
        ),
        "balanced_accuracy": float(
            balanced_accuracy_score(
                y, predictions
            )
        ),
        "brier_score": float(
            brier_score_loss(
                y, probabilities
            )
        ),
        "log_loss": float(
            log_loss(
                y,
                probabilities,
                labels=[0, 1],
            )
        ),
    }


def main():
    for path in (
        TEST_PATH,
        BASE_MODEL_PATH,
        CALIBRATOR_PATH,
    ):
        if not path.exists():
            raise FileNotFoundError(path)

    OUTPUT.mkdir(
        parents=True,
        exist_ok=True,
    )

    df = load_test()

    X = df[FEATURES].replace(
        [np.inf, -np.inf],
        np.nan,
    )

    y = df[
        "target_pagamento_7d"
    ].astype(int).to_numpy()

    if set(np.unique(y)) != {0, 1}:
        raise ValueError(
            "O teste precisa conter as duas classes"
        )

    base_model = joblib.load(
        BASE_MODEL_PATH
    )

    calibrator = joblib.load(
        CALIBRATOR_PATH
    )

    p_original = base_model.predict_proba(
        X
    )[:, 1]

    p_calibrated = calibrator.predict_proba(
        logit(p_original)
    )[:, 1]

    before = evaluate(
        y,
        p_original,
    )

    after = evaluate(
        y,
        p_calibrated,
    )

    results = {
        "period": {
            "start": str(
                df["data_observacao"].min().date()
            ),
            "end": str(
                df["data_observacao"].max().date()
            ),
        },
        "features": FEATURES,
        "before_calibration": before,
        "after_calibration": after,
        "delta_brier": (
            after["brier_score"]
            - before["brier_score"]
        ),
        "delta_log_loss": (
            after["log_loss"]
            - before["log_loss"]
        ),
    }

    predictions = df[
        [
            "contrato_id",
            "data_observacao",
            "target_pagamento_7d",
        ]
    ].copy()

    predictions["probability_original"] = (
        p_original
    )

    predictions["probability_calibrated"] = (
        p_calibrated
    )

    predictions["predicted_class"] = (
        p_calibrated >= 0.5
    ).astype(int)

    predictions.to_parquet(
        OUTPUT / "predictions.parquet",
        index=False,
    )

    # Dez grupos com tamanhos semelhantes.
    # Faixa 10 = maiores probabilidades.
    predictions["decile"] = (
        pd.qcut(
            predictions[
                "probability_calibrated"
            ].rank(method="first"),
            q=10,
            labels=False,
        ) + 1
    )

    deciles = (
        predictions
        .groupby("decile")
        .agg(
            observacoes=(
                "target_pagamento_7d",
                "size",
            ),
            taxa_observada=(
                "target_pagamento_7d",
                "mean",
            ),
            probabilidade_media=(
                "probability_calibrated",
                "mean",
            ),
        )
        .reset_index()
    )

    deciles.to_csv(
        OUTPUT / "payment_by_decile.csv",
        index=False,
        encoding="utf-8-sig",
    )

    # Faixas fixas de probabilidade:
    # permitem inspecionar a calibracao.
    edges = np.linspace(0, 1, 11)

    predictions["probability_band"] = (
        pd.cut(
            predictions[
                "probability_calibrated"
            ],
            bins=edges,
            include_lowest=True,
        )
    )

    calibration = (
        predictions
        .groupby(
            "probability_band",
            observed=True,
        )
        .agg(
            observacoes=(
                "target_pagamento_7d",
                "size",
            ),
            taxa_observada=(
                "target_pagamento_7d",
                "mean",
            ),
            probabilidade_media=(
                "probability_calibrated",
                "mean",
            ),
        )
        .reset_index()
    )

    calibration[
        "probability_band"
    ] = calibration[
        "probability_band"
    ].astype(str)

    calibration.to_csv(
        OUTPUT / "calibration_by_band.csv",
        index=False,
        encoding="utf-8-sig",
    )

    report_path = (
        OUTPUT / "final_metrics.json"
    )

    report_path.write_text(
        json.dumps(
            results,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("\nSTONE | FINAL MODEL EVALUATION")
    print("=" * 70)

    for name, metrics in [
        ("BEFORE CALIBRATION", before),
        ("AFTER CALIBRATION", after),
    ]:
        print(f"\n{name}")

        for key, value in metrics.items():
            if isinstance(value, float):
                print(f"{key}: {value:.4f}")
            else:
                print(f"{key}: {value}")

    print("\nPAYMENT BY DECILE")
    print(
        deciles.to_string(
            index=False
        )
    )

    print("\nCALIBRATION BY BAND")
    print(
        calibration.to_string(
            index=False
        )
    )

    print(
        "\nDelta Brier:",
        f"{results['delta_brier']:+.4f}",
    )

    print(
        "Delta log loss:",
        f"{results['delta_log_loss']:+.4f}",
    )

    print(f"\nRelatorios: {OUTPUT}")
    print("[OK] Avaliacao final concluida")


if __name__ == "__main__":
    main()
