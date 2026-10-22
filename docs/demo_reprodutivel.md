# Demonstração reproduzível com dados sintéticos

## 1. Objetivo

Esta demonstração permite executar um pipeline simplificado de Engenharia de Dados sem acesso aos datasets originais do Stone Data Challenge.

Os dados são inteiramente artificiais e gerados de forma determinística.

A demonstração utiliza uma arquitetura Bronze → Silver → Gold, com testes de integridade e reconciliação financeira.

## 2. Requisitos

- Python 3.12
- UV
- DuckDB
- pytest

As dependências são gerenciadas pelo projeto.

## 3. Instalação

Na raiz do repositório, execute:

```powershell
uv sync
```

## 4. Executar a demonstração

```powershell
uv run python -m stone_data_challenge.demo_pipeline --output data/demo --contracts 100 --seed 42
```

Parâmetros:

| Parâmetro | Descrição |
|---|---|
| `--output` | Diretório dos artefatos gerados |
| `--contracts` | Quantidade de contratos sintéticos |
| `--seed` | Semente utilizada na geração determinística |

## 5. Estrutura dos resultados

```text
data/demo/
├── source/
│   ├── contracts.csv
│   ├── payments.csv
│   └── campaigns.csv
├── bronze/
├── silver/
├── gold/
│   └── contract_summary.parquet
└── demo_report.json
```

A camada Bronze preserva os registros ingeridos em Parquet.

A camada Silver converte os campos para tipos definidos.

A camada Gold consolida indicadores por contrato, incluindo pagamentos e campanhas.

## 6. Executar os testes

```powershell
uv run pytest tests/test_demo_pipeline.py -v
```

A suíte contém 12 testes que verificam:

- Geração dos arquivos sintéticos.
- Reprodutibilidade com semente fixa.
- Validação da quantidade de contratos.
- Integridade dos identificadores.
- Reconciliação financeira.
- Ausência de pagamentos negativos.
- Unicidade de contratos na camada Gold.
- Existência e consistência dos artefatos gerados.

## 7. Integração contínua

O workflow está definido em:

`.github/workflows/demo-ci.yml`

O GitHub Actions executa a instalação do ambiente, o pipeline sintético e os testes independentes da demonstração.

O relatório JSON é disponibilizado como artefato da execução, quando o workflow é concluído com sucesso.

## 8. Limitações

Esta demonstração não reproduz os dados financeiros originais nem o processo completo de treinamento e avaliação do modelo.

As distribuições de pagamentos e campanhas são artificiais e simplificadas.

A finalidade é demonstrar práticas de Engenharia de Dados, testes automatizados e integração contínua.

## 9. Resultado registrado

Uma execução com 100 contratos sintéticos produziu:

| Indicador | Resultado |
|---|---:|
| Contratos | 100 |
| Registros de pagamentos | 3.000 |
| Campanhas | 249 |
| Total simulado de pagamentos | R$ 179.050,00 |
| Reconciliação financeira | Aprovada |
| Testes automatizados | 12 aprovados |

O workflow correspondente também foi validado com sucesso no GitHub Actions.