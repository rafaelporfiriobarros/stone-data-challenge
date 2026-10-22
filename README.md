# Stone Data Challenge

**Engenharia de Dados, Analytics e Machine Learning aplicados à análise de contratos e pagamentos.**

Projeto de portfólio desenvolvido para demonstrar a construção de uma solução de dados de ponta a ponta, desde a ingestão de fontes heterogêneas até a avaliação de modelos preditivos, com atenção à qualidade, rastreabilidade e governança.

> **Status:** projeto analítico implementado e testado. Modelo preditivo classificado como **experimental**.

## 1. Contexto de negócio

O projeto investiga dados relacionados a contratos de crédito, pagamentos, transações financeiras (TPV) e ações de comunicação com clientes.

O desafio é organizar essas informações em uma estrutura analítica confiável e investigar padrões associados à ocorrência de pagamentos.

Entre as perguntas abordadas estão:

- Como integrar informações de contratos, clientes, transações e comunicações?
- Como garantir a consistência dos dados antes de utilizá-los em análises?
- Quais características estão associadas ao indicador de pagamento observado?
- Como avaliar um modelo respeitando a sequência temporal dos dados?
- Como identificar limitações que impedem o uso seguro de um modelo em produção?

## 2. Arquitetura da solução

```mermaid
flowchart TD
    A["Fontes: contratos, TPV, comunicações e clientes"]
    B["Bronze: ingestão"]
    C["Silver: padronização e qualidade"]
    D["Gold: dimensões e fatos"]
    E["Base analítica: observações semanais"]
    F["Machine Learning: treinamento e calibração"]
    G["Avaliação temporal e estabilidade"]
    H["Auditoria e governança"]

    A --> B --> C --> D --> E --> F --> G --> H
```

A arquitetura utiliza Python, DuckDB e Parquet, com separação entre ingestão, tratamento, modelagem analítica e experimentação preditiva.

[Detalhes da arquitetura](docs/arquitetura.md)

## 3. Tecnologias utilizadas

| Tecnologia | Aplicação |
|---|---|
| Python | Desenvolvimento de pipelines, análises e modelos |
| DuckDB | Processamento e consultas analíticas |
| Parquet | Armazenamento colunar |
| pandas e scikit-learn | Processamento analítico e Machine Learning |
| pytest | Testes automatizados |
| UV | Gerenciamento do ambiente Python |
| Git e GitHub | Versionamento |
| GitHub Actions | Integração contínua da demonstração sintética |

## 4. Engenharia de Dados

A solução organiza as fontes em camadas Bronze, Silver e Gold, com verificações de tipos, integridade, unicidade e reconciliação.

### Camada Gold

| Tabela | Registros |
|---|---:|
| Dimensão de clientes | 14.265 |
| Dimensão de contratos | 14.756 |
| Fato diário de contratos | 8.061.006 |
| Fato diário de TPV | 4.408.597 |
| Fato de comunicações | 403.740 |

Esses volumes correspondem aos artefatos analíticos utilizados no desenvolvimento local.

## 5. Machine Learning

Foi construída uma base de observações semanais de contratos para investigar a previsão de um indicador de pagamento em uma janela futura de sete dias.

A base contém **801.725 observações**, distribuídas entre 14.746 contratos.

A avaliação utilizou separação temporal, com intervalo de segurança entre os conjuntos.

| Conjunto | Observações |
|---|---:|
| Treinamento | 696.621 |
| Validação | 58.863 |
| Teste | 31.570 |

Foram avaliados modelos de referência e regressão logística, incluindo calibração de probabilidades.

### Resultados da regressão logística no teste

| Métrica | Resultado |
|---|---:|
| ROC AUC | 0,7849 |
| PR AUC | 0,7208 |
| Brier Score antes da calibração | 0,2527 |
| Brier Score após a calibração | 0,2025 |
| Taxa observada do indicador positivo | 44,82% |
| Probabilidade média prevista após calibração | 54,24% |

Embora a calibração tenha melhorado o Brier Score, a probabilidade média prevista permaneceu aproximadamente **9,42 pontos percentuais acima** da taxa observada.

Esse resultado indica uma limitação relevante de calibração no período de teste.

**Atenção à definição do alvo:** o indicador utilizado é uma aproximação construída a partir da presença de valores positivos em snapshots futuros. Não foi comprovado que ele represente exclusivamente novos pagamentos realizados na janela de sete dias.

Por esse motivo, os resultados não devem ser interpretados como uma previsão validada de recebimentos futuros.

## 6. Qualidade, auditoria e governança

Foram implementadas verificações adicionais para avaliar a consistência da solução:

- **Auditoria do indicador-alvo:** comparação entre a regra utilizada e uma aproximação alternativa baseada em variações positivas.
- **Auditoria temporal das features:** reconstrução de características a partir das datas de observação.
- **Análise de estabilidade:** acompanhamento do comportamento das previsões ao longo do tempo e entre segmentos.
- **Governança:** documentação das métricas, limitações e riscos identificados.

Na auditoria temporal, foram examinadas **97.188 observações** de validação e teste, sem divergências nas seis features reconstruídas.

Esse resultado não comprova, isoladamente, que todos os dados estivessem disponíveis operacionalmente nas respectivas datas.

**Classificação do modelo: EXPERIMENTAL.**

## 7. Testes automatizados

O projeto possui **126 testes aprovados no ambiente local**, cobrindo diferentes componentes da solução.

A suíte completa utiliza dados e artefatos previamente preparados e, portanto, não é executável integralmente a partir de uma instalação limpa sem essas dependências.

Para permitir uma validação independente, foi criada uma demonstração com dados totalmente sintéticos.

## 8. Demonstração reproduzível

A demonstração implementa um fluxo simplificado Bronze → Silver → Gold, sem depender dos dados originais.

Para executar:

```powershell
uv sync
uv run python -m stone_data_challenge.demo_pipeline --output data/demo --contracts 100 --seed 42
uv run pytest tests/test_demo_pipeline.py -v
```

A demonstração gera contratos, pagamentos e campanhas artificiais, aplica transformações e verifica integridade e reconciliação financeira.

**Validação realizada:** 12 testes aprovados localmente e execução bem-sucedida do workflow de integração contínua no GitHub Actions.

[Documentação da demonstração](docs/reproducible_demo.md)

## 9. Limitações

Este projeto é um estudo técnico e não uma solução de decisão de crédito pronta para produção.

As principais limitações identificadas incluem:

1. O indicador-alvo depende da interpretação dos valores presentes nos snapshots.
2. Existe desvio de calibração no período de teste.
3. A disponibilidade operacional histórica das informações não foi integralmente comprovada.
4. As associações entre campanhas e pagamentos não demonstram causalidade.
5. A demonstração sintética não reproduz a distribuição estatística dos dados originais.

Essas limitações são parte da análise técnica e orientam os próximos passos necessários antes de qualquer aplicação operacional.

## 10. Documentação

- [Arquitetura técnica](docs/arquitetura.md)
- [Estudo de caso](docs/estudo_de_caso.md)
- [Metodologia](docs/methodology.md)
- [Resultados](docs/results.md)
- [Limitações](docs/limitations.md)
- [Demonstração reproduzível](docs/reproducible_demo.md)

## 11. Considerações finais

O Stone Data Challenge demonstra a integração entre Engenharia de Dados, Analytics, Machine Learning e práticas de Engenharia de Software.

O principal aprendizado é que desenvolver um modelo com métricas aparentemente satisfatórias não é suficiente. Também é necessário verificar a definição do problema, a confiabilidade dos dados, a consistência temporal e os riscos de utilização dos resultados.

**Projeto independente de portfólio. Não representa uma solução oficial da Stone nem uma implantação em produção.**