
import csv
import random
from datetime import date, timedelta
from pathlib import Path


def write_csv(path: Path, columns: list[str], rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def generate_synthetic_data(
    output_dir: Path,
    n_contracts: int = 100,
    seed: int = 42,
) -> dict[str, Path]:
    if n_contracts < 1:
        raise ValueError("n_contracts deve ser maior que zero")

    rng = random.Random(seed)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    contracts = []
    payments = []
    campaigns = []

    start_date = date(2024, 1, 1)

    for index in range(1, n_contracts + 1):
        contract_id = f"CTR{index:06d}"
        client_id = f"CLI{index:06d}"

        amount = rng.randint(1000, 20000)
        term = rng.choice([90, 180, 270, 360])
        retention = rng.choice([0.05, 0.10, 0.15, 0.20])

        contracts.append({
            "contrato_id": contract_id,
            "cliente_id": client_id,
            "data_contrato": start_date.isoformat(),
            "vlr_desembolsado": amount,
            "prazo": term,
            "perc_retencao": retention,
        })

        for day in range(1, 31):
            payment_date = start_date + timedelta(days=day)
            payment_amount = rng.choice([0, 0, 0, 50, 100, 200])

            payments.append({
                "contrato_id": contract_id,
                "data_pagamento": payment_date.isoformat(),
                "valor_pagamento": payment_amount,
            })

        for day in [3, 10, 17, 24]:
            if rng.random() < 0.6:
                campaigns.append({
                    "contrato_id": contract_id,
                    "data_acao": (
                        start_date + timedelta(days=day)
                    ).isoformat(),
                    "acao": rng.choice([
                        "EMAIL",
                        "SMS",
                        "WHATSAPP",
                    ]),
                })

    paths = {
        "contracts": output_dir / "contracts.csv",
        "payments": output_dir / "payments.csv",
        "campaigns": output_dir / "campaigns.csv",
    }

    write_csv(
        paths["contracts"],
        [
            "contrato_id",
            "cliente_id",
            "data_contrato",
            "vlr_desembolsado",
            "prazo",
            "perc_retencao",
        ],
        contracts,
    )

    write_csv(
        paths["payments"],
        [
            "contrato_id",
            "data_pagamento",
            "valor_pagamento",
        ],
        payments,
    )

    write_csv(
        paths["campaigns"],
        [
            "contrato_id",
            "data_acao",
            "acao",
        ],
        campaigns,
    )

    return paths
