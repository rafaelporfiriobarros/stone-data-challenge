# Resultados — Stone Data Challenge

## 1. Resumo

O projeto implementou uma solução de Engenharia de Dados e Analytics, acompanhada de experimentação preditiva, testes automatizados e auditorias de confiabilidade.

Os resultados descritos neste documento correspondem às execuções realizadas durante o desenvolvimento.

## 2. Volumes processados

### Camada Gold

| Entidade | Registros |
|---|---:|
| Dimensão de clientes | 14.265 |
| Dimensão de contratos | 14.756 |
| Fato diário de contratos | 8.061.006 |
| Fato diário de TPV | 4.408.597 |
| Fato de comunicações | 403.740 |

### Base de Machine Learning

| Indicador | Resultado |
|---|---:|
| Observações semanais | 801.725 |
| Contratos distintos | 14.746 |
| Observações de treinamento | 696.621 |
| Observações de validação | 58.863 |
| Observações de teste | 31.570 |

## 3. Avaliação do modelo

Resultados da regressão logística no conjunto de teste:

| Métrica | Resultado |
|---|---:|
| ROC AUC | 0,7849 |
| PR AUC | 0,7208 |
| Brier Score antes da calibração | 0,2527 |
| Brier Score após a calibração | 0,2025 |

A calibração reduziu o Brier Score, mas não eliminou a diferença entre probabilidades previstas e frequências observadas.

### Desvio de calibração

| Indicador | Resultado |
|---|---:|
| Taxa observada de indicador positivo | 44,82% |
| Probabilidade média prevista após calibração | 54,24% |
| Diferença aproximada | +9,42 pontos percentuais |

O modelo apresentou superestimação média das probabilidades no conjunto de teste.

## 4. Estabilidade temporal

A avaliação por semanas do período de teste identificou aumento do desvio entre as probabilidades previstas e as taxas observadas.

Esse comportamento sugere alteração no desempenho probabilístico ao longo do tempo e reforça a necessidade de monitoramento e reavaliação antes de qualquer aplicação operacional.

## 5. Auditoria do indicador-alvo

| Verificação | Resultado |
|---|---:|
| Janelas completas analisadas | 97.188 |
| Divergências na reconstrução da regra original | 0 |
| Divergências em relação à aproximação por variação positiva | 723 |
| Percentual de divergências | Aproximadamente 0,74% |

A ausência de divergências na reconstrução comprova consistência da implementação da regra analisada, mas não valida sua interpretação financeira.

## 6. Auditoria temporal das características

| Indicador | Resultado |
|---|---:|
| Observações auditadas | 97.188 |
| Características reconstruídas | 6 |
| Divergências identificadas | 0 |
| Registros de portfólio ausentes | 0 |

A auditoria confirmou a consistência das características em relação às regras históricas implementadas.

Entretanto, a disponibilidade operacional dos eventos nas respectivas datas não foi comprovada integralmente.

## 7. Demonstração sintética

Foi desenvolvido um pipeline independente com dados artificiais.

Na execução documentada:

| Indicador | Resultado |
|---|---:|
| Contratos sintéticos | 100 |
| Registros de pagamentos | 3.000 |
| Campanhas | 249 |
| Valor total simulado | R$ 179.050,00 |
| Reconciliação financeira | Aprovada |
| Testes da demonstração | 12 aprovados |

Esses valores são exclusivamente sintéticos.

## 8. Qualidade de software

A suíte completa registrou **126 testes aprovados** no ambiente local.

O workflow de integração contínua da demonstração sintética também foi executado com sucesso no GitHub Actions.

A suíte completa depende de artefatos locais previamente gerados, enquanto a demonstração sintética pode ser executada independentemente dos dados originais.

## 9. Interpretação

O projeto demonstra a capacidade de estruturar dados, implementar verificações de qualidade, construir modelos experimentais e investigar criticamente seus resultados.

Os indicadores preditivos não devem ser apresentados como evidência de desempenho em produção.

A classificação atual do modelo é **EXPERIMENTAL**.