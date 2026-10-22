
import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from stone_data_challenge.config import DATA_DIR, REPORTS_DIR


OUTPUT = REPORTS_DIR / "model_governance"

PREDICTIONS = (
    REPORTS_DIR / "final_evaluation" / "predictions.parquet"
)

SPLITS = {
    "train": DATA_DIR / "ml" / "train.parquet",
    "validation": DATA_DIR / "ml" / "validation.parquet",
    "test": DATA_DIR / "ml" / "test.parquet",
}

AUDITS = {
    "target_integrity": (
        REPORTS_DIR
        / "target_integrity"
        / "target_integrity_report.json"
    ),
    "point_in_time": (
        REPORTS_DIR
        / "point_in_time_audit"
        / "point_in_time_report.json"
    ),
}

FEATURES = [
    "prazo",
    "vlr_desembolsado",
    "perc_retencao",
    "campanhas_7d",
    "campanhas_30d",
    "dias_com_acionamento_30d",
]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def parquet_relation(con, path: Path):
    # Evita interpolar caminhos em comandos SQL.
    return con.from_parquet(str(path))


def get_split_metrics(con, path: Path):
    relation = parquet_relation(con, path)

    result = relation.aggregate(
        """
        COUNT(*) AS observations,
        COUNT(DISTINCT contrato_id) AS contracts,
        MIN(data_observacao) AS first_date,
        MAX(data_observacao) AS last_date,
        AVG(target_pagamento_7d) AS positive_rate
        """
    ).fetchall()[0]

    return {
        "observations": result[0],
        "contracts": result[1],
        "first_date": str(result[2]),
        "last_date": str(result[3]),
        "positive_rate": float(result[4]),
    }


def get_prediction_metrics(con):
    relation = parquet_relation(con, PREDICTIONS)

    result = relation.aggregate(
        """
        COUNT(*) AS observations,
        COUNT(DISTINCT (
            contrato_id,
            data_observacao
        )) AS unique_keys,
        AVG(target_pagamento_7d) AS observed_rate,
        AVG(probability_calibrated) AS predicted_rate,
        AVG(
            POWER(
                probability_calibrated
                - target_pagamento_7d,
                2
            )
        ) AS brier_score
        """
    ).fetchall()[0]

    return {
        "observations": result[0],
        "unique_keys": result[1],
        "observed_rate": float(result[2]),
        "predicted_rate": float(result[3]),
        "calibration_gap_pp": round(
            100 * (float(result[3]) - float(result[2])),
            4,
        ),
        "brier_score": float(result[4]),
    }


def build_risks(target_audit, point_audit, predictions):
    risks = [
        {
            "id": "R001",
            "severity": "HIGH",
            "category": "target_semantics",
            "status": "OPEN",
            "description": (
                "A variavel target indica presenca de "
                "valor positivo em snapshots futuros. "
                "Ainda nao ha comprovacao independente "
                "de que representa novo pagamento."
            ),
            "recommendation": (
                "Validar a semantica de vlr_pgto_realizado "
                "com documentacao da fonte ou eventos "
                "financeiros transacionais."
            ),
        },
        {
            "id": "R002",
            "severity": "HIGH",
            "category": "temporal_drift",
            "status": "OPEN",
            "description": (
                "O modelo superestima a taxa positiva "
                "no conjunto de teste."
            ),
            "evidence": {
                "calibration_gap_pp": (
                    predictions["calibration_gap_pp"]
                )
            },
            "recommendation": (
                "Monitorar calibracao por periodo e "
                "avaliar estrategias de recalibracao "
                "em validacoes temporais futuras."
            ),
        },
        {
            "id": "R003",
            "severity": "MEDIUM",
            "category": "data_availability",
            "status": "OPEN",
            "description": (
                "A consistencia historica das features "
                "foi auditada, mas a disponibilidade "
                "operacional no instante da previsao "
                "nao foi comprovada."
            ),
            "recommendation": (
                "Incorporar timestamps de ingestao "
                "e disponibilidade das fontes."
            ),
        },
        {
            "id": "R004",
            "severity": "MEDIUM",
            "category": "causal_interpretation",
            "status": "OPEN",
            "description": (
                "A associacao entre campanhas e target "
                "nao demonstra efeito causal."
            ),
            "recommendation": (
                "Nao interpretar o ganho preditivo "
                "como impacto incremental de campanhas."
            ),
        },
    ]

    return risks


def markdown_report(report):
    splits = report["splits"]
    predictions = report["predictions"]
    target = report["audits"]["target_integrity"]
    point = report["audits"]["point_in_time"]

    target_metrics = target["comparacao_targets"]
    feature_metrics = point["features"]

    lines = [
        "# Stone Data Challenge",
        "",
        "## Model Governance & Technical Report",
        "",
        f"Gerado em: {report['generated_at']}",
        "",
        "## 1. Objetivo",
        "",
        "Avaliar um modelo preditivo associado ao "
        "comportamento de pagamentos de contratos, "
        "utilizando dados de carteira e comunicacoes.",
        "",
        "**Restricao:** o target ainda nao foi "
        "validado como novo pagamento financeiro.",
        "",
        "## 2. Arquitetura",
        "",
        "Bronze -> Silver -> Gold -> Analytics -> "
        "Machine Learning -> Auditorias.",
        "",
        "Tecnologias: Python, DuckDB, Parquet, "
        "scikit-learn, UV e pytest.",
        "",
        "## 3. Divisao temporal",
        "",
        "| Split | Observacoes | Inicio | Fim | "
        "Taxa positiva |",
        "|---|---:|---|---|---:|",
    ]

    for name, data in splits.items():
        lines.append(
            f"| {name} | {data['observations']:,} | "
            f"{data['first_date']} | "
            f"{data['last_date']} | "
            f"{data['positive_rate']:.2%} |"
        )

    lines.extend([
        "",
        "A separacao temporal utiliza embargo "
        "entre os conjuntos.",
        "",
        "## 4. Features do modelo",
        "",
    ])

    for feature in report["features"]:
        lines.append(f"- `{feature}`")

    lines.extend([
        "",
        "## 5. Avaliacao no teste",
        "",
        f"- Observacoes: {predictions['observations']:,}",
        f"- Taxa observada: "
        f"{predictions['observed_rate']:.2%}",
        f"- Probabilidade media prevista: "
        f"{predictions['predicted_rate']:.2%}",
        f"- Desvio de calibracao: "
        f"{predictions['calibration_gap_pp']:.2f} p.p.",
        f"- Brier Score: "
        f"{predictions['brier_score']:.4f}",
        "",
        "As metricas representam desempenho "
        "preditivo do target operacional.",
        "",
        "## 6. Auditoria do target",
        "",
        f"- Observacoes auditadas: "
        f"{target_metrics['observacoes']:,}",
        f"- Janelas completas: "
        f"{target_metrics['janelas_completas']:,}",
        f"- Divergencias versus incremento: "
        f"{target_metrics['divergencias_incremento']:,}",
        "",
        "A comparacao com incrementos e exploratoria "
        "e nao comprova a ocorrencia de novos pagamentos.",
        "",
        "## 7. Auditoria point-in-time",
        "",
        f"- Observacoes: "
        f"{feature_metrics['observacoes']:,}",
        f"- Chaves unicas: "
        f"{feature_metrics['chaves_unicas']:,}",
        f"- Snapshots ausentes: "
        f"{feature_metrics['missing_portfolio']:,}",
        "",
        "Divergencias por feature:",
        "",
    ])

    for key, value in feature_metrics.items():
        if key.startswith("mismatch_"):
            lines.append(f"- `{key}`: {value}")

    lines.extend([
        "",
        "A auditoria demonstra consistencia historica, "
        "nao disponibilidade em tempo real.",
        "",
        "## 8. Registro de riscos",
        "",
        "| ID | Severidade | Categoria | Status |",
        "|---|---|---|---|",
    ])

    for risk in report["risks"]:
        lines.append(
            f"| {risk['id']} | {risk['severity']} | "
            f"{risk['category']} | {risk['status']} |"
        )

    lines.extend([
        "",
        "## 9. Recomendacoes",
        "",
        "1. Validar a definicao financeira do target.",
        "2. Registrar timestamps de disponibilidade.",
        "3. Monitorar drift e calibracao temporal.",
        "4. Manter a interpretacao observacional "
        "das campanhas.",
        "5. Reavaliar o modelo antes de qualquer "
        "utilizacao operacional.",
        "",
        "## 10. Conclusao",
        "",
        "O projeto demonstra um pipeline analitico "
        "reproduzivel, com testes e auditorias.",
        "O modelo permanece experimental e nao deve "
        "ser considerado validado para decisao "
        "financeira em producao.",
        "",
    ])

    return "\n".join(lines)


def main():
    required = [
        PREDICTIONS,
        *SPLITS.values(),
        *AUDITS.values(),
    ]

    for path in required:
        if not path.exists():
            raise FileNotFoundError(path)

    OUTPUT.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()

    try:
        splits = {
            name: get_split_metrics(con, path)
            for name, path in SPLITS.items()
        }

        predictions = get_prediction_metrics(con)

    finally:
        con.close()

    if predictions["observations"] != splits["test"]["observations"]:
        raise ValueError(
            "Quantidade de previsoes diferente "
            "do conjunto de teste."
        )

    if predictions["unique_keys"] != predictions["observations"]:
        raise ValueError(
            "Chaves duplicadas nas previsoes."
        )

    target_audit = load_json(AUDITS["target_integrity"])
    point_audit = load_json(AUDITS["point_in_time"])

    report = {
        "project": "Stone Data Challenge",
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "model_status": "EXPERIMENTAL",
        "target_definition": (
            "Existe valor positivo de "
            "vlr_pgto_realizado nos sete dias "
            "posteriores a observacao."
        ),
        "features": FEATURES,
        "splits": splits,
        "predictions": predictions,
        "audits": {
            "target_integrity": target_audit,
            "point_in_time": point_audit,
        },
        "risks": build_risks(
            target_audit,
            point_audit,
            predictions,
        ),
    }

    json_path = OUTPUT / "model_governance_report.json"
    md_path = OUTPUT / "model_governance_report.md"

    json_path.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    md_path.write_text(
        markdown_report(report),
        encoding="utf-8",
    )

    print("\nSTONE | MODEL GOVERNANCE")
    print("=" * 60)

    for name, data in splits.items():
        print(
            f"{name}: {data['observations']} observacoes"
        )

    print(
        "Brier Score:",
        round(predictions["brier_score"], 4),
    )

    print(
        "Desvio de calibracao:",
        round(predictions["calibration_gap_pp"], 2),
        "p.p.",
    )

    print("Riscos documentados:", len(report["risks"]))
    print("Status:", report["model_status"])

    print("\nArquivos gerados:")
    print(json_path)
    print(md_path)

    print("\n[OK] Governanca consolidada")


if __name__ == "__main__":
    main()
