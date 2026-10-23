# Stone Data Challenge — Conclusão de Negócio

## 1. Pergunta de negócio

Quais características financeiras dos contratos e quais padrões de comunicação estão associados ao indicador de pagamento nos sete dias seguintes?

O estudo busca compreender padrões históricos e avaliar se informações sobre campanhas acrescentam capacidade preditiva às características financeiras dos contratos.

**Limitação fundamental:** o indicador `target_pagamento_7d` representa a regra implementada a partir de snapshots financeiros futuros. Ainda não foi validado como representação inequívoca de novos pagamentos realizados durante a janela de sete dias.

## 2. Universo analisado

| Indicador | Resultado |
|---|---:|
| Observações semanais | 801.725 |
| Contratos distintos | 14.746 |
| Observações com indicador positivo | 622.468 |
| Taxa geral do indicador positivo | 77,64% |
| Início do período | 06/01/2020 |
| Fim do período | 11/04/2022 |

A unidade de análise é uma observação semanal por contrato. Um contrato pode contribuir com diversas observações, de modo que os registros não devem ser interpretados como eventos independentes.

## 3. Principais descobertas financeiras

### Valor desembolsado

| Valor desembolsado | Taxa positiva |
|---|---:|
| Abaixo de R$ 2 mil | 61,07% |
| R$ 2 mil a menos de R$ 5 mil | 67,14% |
| R$ 5 mil a menos de R$ 10 mil | 71,99% |
| R$ 10 mil ou mais | 80,00% |

A taxa do indicador positivo cresce entre as faixas de valor examinadas, com diferença de 18,93 pontos percentuais entre os extremos.

Esse resultado indica associação descritiva, não efeito causal do valor desembolsado.

### Prazo contratual

| Prazo | Taxa positiva |
|---|---:|
| Até 12 meses | 67,32% |
| 13 a 24 meses | 67,60% |
| 25 a 36 meses | 79,11% |

O grupo de 25 a 36 meses apresenta a maior taxa e concentra a maioria das observações.

A distribuição desigual exige cautela ao comparar os segmentos.

## 4. Comunicação e indicador de pagamento

| Campanhas nos últimos 30 dias | Observações | Taxa positiva |
|---|---:|---:|
| Nenhuma | 502.912 | 86,74% |
| Uma | 122.670 | 64,70% |
| Duas a três | 109.402 | 68,11% |
| Quatro ou mais | 66.741 | 48,49% |

A diferença entre nenhuma campanha e quatro ou mais campanhas é de 38,25 pontos percentuais.

O resultado demonstra uma associação negativa no agregado, mas não permite concluir que campanhas reduzam pagamentos.

Uma explicação possível é a seleção de contratos com maior risco para ações de comunicação. Essa hipótese ainda precisa de investigação específica.

## 5. Análise segmentada

A comparação por faixas de valor desembolsado e prazo mostrou que as observações sem campanhas apresentaram taxas positivas superiores às observações com quatro ou mais campanhas em todos os segmentos examinados.

Um exemplo é o segmento com valor desembolsado de R$ 10 mil ou mais e prazo superior a 24 meses:

| Campanhas | Taxa positiva |
|---|---:|
| Nenhuma | 89,49% |
| Uma a três | 67,98% |
| Quatro ou mais | 47,85% |

A diferença entre os extremos é de 41,64 pontos percentuais.

O padrão não parece decorrer exclusivamente da composição por essas faixas de valor e prazo. Entretanto, a segmentação não controla integralmente histórico financeiro, seleção de campanhas, tempo ou características não observadas.

## 6. Valor preditivo das comunicações

Foi realizada uma comparação entre dois modelos na mesma amostra de validação temporal, composta por 58.863 observações.

O primeiro utilizou características financeiras:

- Prazo
- Valor desembolsado
- Percentual de retenção

O segundo acrescentou:

- Campanhas nos últimos sete dias
- Campanhas nos últimos 30 dias
- Dias com acionamento nos últimos 30 dias

| Métrica | Financeiro | Financeiro + comunicações |
|---|---:|---:|
| ROC AUC | 0,7745 | 0,8047 |
| PR AUC | 0,7592 | 0,8156 |
| Brier Score | 0,2134 | 0,2087 |
| Log Loss | 0,6311 | 0,6274 |

As características de comunicação produziram ganhos de aproximadamente 0,0302 no ROC AUC e 0,0564 no PR AUC, além de reduções no Brier Score e no Log Loss.

**Conclusão:** o histórico de comunicações acrescentou informação preditiva às características financeiras nesse experimento de validação.

O ganho estatístico não representa evidência de impacto causal das campanhas nem de aumento da recuperação financeira.

As probabilidades previstas também apresentaram superestimação em relação à taxa observada.

## 7. Auditorias e confiabilidade

O projeto incluiu auditorias específicas da construção do indicador-alvo e das características temporais.

Na auditoria do indicador, foram encontradas 723 divergências entre a regra original e uma aproximação baseada em variações positivas de valores financeiros, em 97.188 janelas completas.

Na auditoria temporal, a reconstrução das seis características examinadas apresentou zero divergências nas 97.188 observações auditadas.

Esses resultados sustentam a consistência das regras implementadas, mas não comprovam integralmente a semântica do evento financeiro nem a disponibilidade operacional histórica de todas as informações.

## 8. Robustez temporal

A análise trimestral contemplou dez trimestres, entre janeiro de 2020 e abril de 2022, sendo o último trimestre parcial.

Os resultados mostram que a associação entre frequência de campanhas e o indicador positivo é recorrente ao longo do período.

As observações sem campanhas apresentaram taxas superiores às observações com uma a três campanhas em todos os trimestres analisados.

A comparação com a faixa de quatro ou mais campanhas também indica taxas geralmente inferiores, embora a relação não seja perfeitamente monotônica em todos os períodos.

Além disso, foram identificadas mudanças relevantes nas taxas do indicador ao longo do tempo.

Entre o terceiro trimestre de 2020 e o primeiro trimestre de 2022, a taxa do grupo sem campanhas passou de 97,03% para 59,98%, uma redução de 37,05 pontos percentuais.

Esse comportamento indica que o período de observação é uma dimensão importante para a interpretação dos resultados.

A recorrência da associação fortalece sua relevância descritiva, mas não demonstra causalidade, estabilidade das relações condicionais ou capacidade preditiva constante ao longo do tempo.

As observações repetidas por contrato e possíveis mudanças na composição da carteira permanecem como limitações.

**Conclusão da robustez temporal:** o padrão geral entre frequência de campanhas e indicador positivo se repete em diferentes períodos, mas as taxas variam substancialmente ao longo do tempo. Portanto, qualquer utilização operacional exigiria monitoramento temporal, investigação dos fatores associados às mudanças e validação adicional do indicador-alvo.

## 9. Resposta à pergunta de negócio

As análises identificaram associações relevantes entre o indicador de pagamento e características financeiras dos contratos, especialmente valor desembolsado e prazo.

A frequência de campanhas também apresentou associação com o indicador, inclusive dentro dos segmentos financeiros examinados.

Além disso, as características de comunicação acrescentaram capacidade preditiva ao modelo financeiro na validação temporal.

Portanto, a pergunta foi **respondida no âmbito descritivo e preditivo do indicador construído**, sujeita às limitações metodológicas documentadas.

Não há evidência suficiente para afirmar que campanhas provocam aumento ou redução de pagamentos, nem para recomendar alterações operacionais baseadas em efeitos causais.

## 10. Recomendações

1. Validar com as regras financeiras do negócio o significado do indicador de pagamento.
2. Investigar os critérios utilizados para selecionar contratos para campanhas.
3. Avaliar a estabilidade temporal das associações.
4. Verificar a calibração e a robustez das probabilidades antes de qualquer aplicação operacional.
5. Considerar experimentos controlados ou métodos causais adequados caso o objetivo seja estimar o efeito das campanhas.

## 11. Conclusão

O Stone Data Challenge demonstrou que a integração de dados financeiros, contratuais e de comunicação permite produzir análises segmentadas e acrescentar informação a experimentos preditivos.

O principal resultado não é uma recomendação automática de campanhas, mas a identificação de padrões que podem orientar investigações mais específicas.

A confiabilidade das decisões depende tanto da qualidade técnica dos pipelines quanto da validade das definições de negócio e da interpretação adequada das evidências.

**Status:** estudo analítico e preditivo experimental, sem validação para decisões financeiras operacionais.