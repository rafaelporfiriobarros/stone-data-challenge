
import json

import duckdb
import joblib
import numpy as np

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    brier_score_loss,
    log_loss,
    roc_auc_score,
)

from stone_data_challenge.config import DATA_DIR, REPORTS_DIR
from stone_data_challenge.train_baseline import (
    FEATURES,
    load_split,
)


MODEL_DIR = DATA_DIR / "models"
VALIDATION_PATH = DATA_DIR / "ml" / "validation.parquet"
REPORT = REPORTS_DIR / "calibration_metrics.json"

BASE_MODEL = MODEL_DIR / "financial_plus_campaigns.joblib"
CALIBRATOR_PATH = MODEL_DIR / "campaign_calibrator.joblib"

CALIBRATION_END = "2022-01-31"
CHECK_START = "2022-02-07"


def logit(probabilities):
    p = np.clip(
        np.asarray(probabilities, dtype=float),
        1e-6,
        1 - 1e-6,
    )
    return np.log(p / (1 - p)).reshape(-1, 1)


def metrics(y, probabilities):
    return {
        "observacoes": int(len(y)),
        "taxa_observada": float(np.mean(y)),
        "probabilidade_media": float(
            np.mean(probabilities)
        ),
        "roc_auc": float(
            roc_auc_score(y, probabilities)
        ),
        "brier_score": float(
            brier_score_loss(y, probabilities)
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
    if not BASE_MODEL.exists():
        raise FileNotFoundError(
            "Execute campaign_ablation.py primeiro"
        )

    X_val, y_val = load_split("validation")

    con = duckdb.connect()
    try:
        dates = con.execute(
            """
            SELECT data_observacao
            FROM read_parquet(?)
            """,
            [str(VALIDATION_PATH)],
        ).fetchnumpy()["data_observacao"]
    finally:
        con.close()

    if len(dates) != len(X_val):
        raise ValueError(
            "Datas e features com tamanhos diferentes"
        )

    # As consultas de load_split e de datas leem o
    # mesmo Parquet sem ORDER BY. Para garantir
    # alinhamento, carregamos a data como chave
    # e validamos a ordenacao explicitamente.
    con = duckdb.connect()
    try:
        ordered = con.execute(
            """
            SELECT
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
            [str(VALIDATION_PATH)],
        ).fetchdf()
    finally:
        con.close()

    X = ordered[FEATURES].replace(
        [np.inf, -np.inf], np.nan
    )
    y = ordered["target_pagamento_7d"].astype(int)

    calibration_mask = (
        ordered["data_observacao"]
        <= CALIBRATION_END
    )
    check_mask = (
        ordered["data_observacao"]
        >= CHECK_START
    )

    if (
        calibration_mask.sum() == 0
        or check_mask.sum() == 0
    ):
        raise ValueError(
            "Periodos de calibracao invalidos"
        )

    base_model = joblib.load(BASE_MODEL)

    p_cal = base_model.predict_proba(
        X.loc[calibration_mask]
    )[:, 1]

    p_check = base_model.predict_proba(
        X.loc[check_mask]
    )[:, 1]

    y_cal = y.loc[calibration_mask]
    y_check = y.loc[check_mask]

    if y_cal.nunique() != 2 or y_check.nunique() != 2:
        raise ValueError(
            "Ambos os periodos precisam ter duas classes"
        )

    calibrator = LogisticRegression(
        max_iter=1000,
        random_state=42,
    )

    calibrator.fit(
        logit(p_cal),
        y_cal,
    )

    p_check_calibrated = (
        calibrator.predict_proba(
            logit(p_check)
        )[:, 1]
    )

    before = metrics(y_check, p_check)
    after = metrics(
        y_check,
        p_check_calibrated,
    )

    report = {
        "calibration_end": CALIBRATION_END,
        "check_start": CHECK_START,
        "calibration_observations": int(
            calibration_mask.sum()
        ),
        "check_observations": int(
            check_mask.sum()
        ),
        "before": before,
        "after": after,
        "delta_brier": (
            after["brier_score"]
            - before["brier_score"]
        ),
        "delta_log_loss": (
            after["log_loss"]
            - before["log_loss"]
        ),
        "calibrator_coefficient": float(
            calibrator.coef_[0, 0]
        ),
    }

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    joblib.dump(
        calibrator,
        CALIBRATOR_PATH,
    )

    REPORT.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("\nSTONE | TEMPORAL CALIBRATION")
    print("=" * 70)

    for name in ("before", "after"):
        print(f"\n{name.upper()}")
        for key, value in report[name].items():
            print(f"{key}: {value:.4f}")

    print(
        "\nDelta Brier:",
        f"{report['delta_brier']:+.4f}",
    )
    print(
        "Delta log loss:",
        f"{report['delta_log_loss']:+.4f}",
    )
    print(
        "Coeficiente:",
        f"{report['calibrator_coefficient']:.4f}",
    )
    print("\n[OK] Calibracao temporal concluida")


if __name__ == "__main__":
    main()
