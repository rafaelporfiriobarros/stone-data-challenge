# Stone Data Challenge

**End-to-End Data Engineering, Analytics & Machine Learning**

Projeto de Engenharia de Dados e Machine Learning desenvolvido para analisar dados de contratos financeiros, transações e comunicações, com foco na construção de uma base analítica confiável e na avaliação de um modelo preditivo de comportamento de pagamentos.

## 1. Contexto de negócio

Em operações de crédito vinculadas a recebíveis de vendas, compreender o comportamento financeiro dos contratos pode apoiar atividades de acompanhamento de carteira e planejamento operacional.

O projeto investiga a relação entre características contratuais, histórico de comunicações e um indicador de pagamento observado nos sete dias seguintes.

**Importante:** o indicador utilizado representa a presença de valores positivos no campo `vlr_pgto_realizado` em snapshots futuros. Sua equivalência a novos pagamentos financeiros ainda não foi comprovada.

## 2. Objetivos

- Integrar dados de diferentes fontes em uma arquitetura analítica.
- Implementar pipelines de ingestão, padronização e transformação.
- Construir tabelas dimensionais e fatos em Parquet.
- Desenvolver análises exploratórias de carteira e comunicações.
- Criar um dataset supervisionado com janelas temporais.
- Treinar e avaliar modelos preditivos.
- Auditar a integridade do target e a consistência histórica das features.
- Documentar riscos, resultados e limitações.

## 3. Arquitetura

```text
Fontes de dados
      |
      v
    Bronze
      |
      v
    Silver
      |
      v
     Gold
      |
      +----> Analytics / EDA
      |
      v
  ML Dataset
      |
      v
Temporal Split
      |
      v
Model Training
      |
      v
Calibration & Evaluation
      |
      v
Audits & Governance
```

A solução utiliza armazenamento local em Parquet e processamento analítico com DuckDB.

## 4. Tecnologias

| Tecnologia | Aplicação |
|---|---|
| Python | Pipelines e análises |
| DuckDB | Consultas e transformações analíticas |
| Parquet | Armazenamento colunar |
| scikit-learn | Treinamento, calibração e avaliação |
| pytest | Testes automatizados |
| UV | Gerenciamento do ambiente Python |
| Git | Versionamento do projeto |

## 5. Camada Gold

A arquitetura analítica contém:

| Tabela | Registros |
|---|---:|
| `fact_contrato_diario` | 8.061.006 |
| `fact_tpv_diario` | 4.408.597 |
| `fact_comunicacoes` | 403.740 |
| `dim_clientes` | 14.265 |
| `dim_contratos` | 14.756 |

Foram implementadas verificações de integridade, unicidade e reconciliação entre camadas.

## 6. Machine Learning

O dataset supervisionado contém 801.725 observações semanais.

### Variáveis utilizadas

- `prazo`
- `vlr_desembolsado`
- `perc_retencao`
- `campanhas_7d`
- `campanhas_30d`
- `dias_com_acionamento_30d`

### Divisão temporal

| Conjunto | Observações |
|---|---:|
| Treinamento | 696.621 |
| Validação | 58.863 |
| Teste | 31.570 |

Foi utilizado um intervalo de embargo de 14 dias entre os conjuntos, visando reduzir a sobreposição temporal entre as janelas de previsão.

### Modelos

Foram avaliados um modelo de referência (*Dummy Classifier*) e uma regressão logística, incluindo experimentos de ablação das features de campanhas e calibração de probabilidades.

## 7. Resultados

| Métrica | Resultado |
|---|---:|
| ROC-AUC no teste | 0,7849 |
| PR-AUC no teste | 0,7208 |
| Brier Score antes da calibração | 0,2527 |
| Brier Score após a calibração | 0,2025 |
| Desvio médio de calibração | +9,42 p.p. |

A calibração reduziu o Brier Score, mas o modelo continuou superestimando a taxa positiva observada no teste.

Essas métricas avaliam a previsão do target operacional definido neste projeto e não comprovam capacidade de prever novos pagamentos financeiros.

## 8. Auditorias e governança

### Target Integrity Audit

- 97.188 observações auditadas.
- 100% das janelas analisadas estavam completas.
- Nenhuma divergência entre o target armazenado e sua reconstrução operacional.
- 723 divergências na comparação exploratória com um target baseado em incrementos.

### Point-in-Time Audit

- 97.188 observações auditadas.
- Nenhum snapshot financeiro ausente.
- Nenhuma divergência na reconstrução das seis features.

A auditoria valida consistência histórica segundo as regras implementadas, mas não comprova disponibilidade operacional em tempo real.

### Model Governance

Foram documentados quatro riscos: semântica do target, desvio temporal de calibração, disponibilidade dos dados e interpretação causal das campanhas.

**Status do modelo: EXPERIMENTAL.**

## 9. Qualidade e testes

A suíte automatizada possui **114 testes aprovados**, abrangendo ingestão, Silver, Gold, construção do dataset, divisão temporal, treinamento, avaliação e auditorias.

Execução dos testes:

```powershell
uv sync
uv run pytest -v
```

Os testes de integração dependem dos artefatos de dados previamente gerados. Os dados originais não são distribuídos automaticamente neste repositório.

## 10. Limitações

1. A definição financeira do target precisa ser validada com a fonte de origem.
2. A disponibilidade operacional das features não foi comprovada por timestamps de ingestão.
3. O modelo apresenta superestimação das probabilidades no período de teste.
4. A relação entre campanhas e comportamento financeiro é observacional, não causal.
5. A disponibilidade temporal das fontes varia; o histórico de TPV não cobre todo o período de avaliação.

## 11. Conclusão

O Stone Data Challenge demonstra a construção de uma solução de dados ponta a ponta, integrando engenharia de dados, modelagem analítica, aprendizado supervisionado, testes automatizados e governança.

O principal resultado do projeto não é apenas o desempenho preditivo, mas a capacidade de construir uma solução rastreável, reproduzível e tecnicamente auditável, identificando também as limitações que impedem sua utilização imediata em produção.

**Projeto de estudo e portfólio técnico. Não representa um sistema financeiro em produção.**