# Metodologia — Stone Data Challenge

## 1. Objetivo

Documentar os procedimentos utilizados na preparação dos dados, construção da base analítica, experimentação de Machine Learning e avaliação da confiabilidade dos resultados.

O projeto investiga padrões associados a um indicador de pagamento de contratos, sem pressupor que os resultados possam ser utilizados diretamente em decisões financeiras.

## 2. Preparação dos dados

O processamento foi organizado em três camadas:

- **Bronze:** ingestão e preservação das informações de origem.
- **Silver:** padronização de tipos, tratamento e verificações de qualidade.
- **Gold:** organização em dimensões e fatos para consumo analítico.

Foram trabalhadas informações de contratos, clientes, transações financeiras (TPV) e comunicações.

A modelagem respeita a granularidade de cada entidade, especialmente as chaves de contratos, datas e registros de comunicação.

## 3. Construção da base analítica

A base utilizada nos experimentos contém 801.725 observações semanais, referentes a 14.746 contratos.

As observações foram construídas em datas de referência semanais, às segundas-feiras, entre janeiro de 2020 e abril de 2022.

Cada registro representa um contrato em uma data de observação.

## 4. Definição do indicador-alvo

Foi construído o indicador `target_pagamento_7d`, definido como a presença de pelo menos um valor positivo no campo `vlr_pgto_realizado` em snapshots dos sete dias seguintes à observação.

Essa definição é uma aproximação operacional para fins de experimentação.

**Limitação importante:** não foi comprovado que o campo represente exclusivamente novos pagamentos realizados durante a janela futura.

Consequentemente, o indicador não deve ser apresentado como uma medida validada de recebimento futuro.

## 5. Características utilizadas

O modelo utiliza seis características:

| Característica | Interpretação |
|---|---|
| `prazo` | Prazo do contrato |
| `vlr_desembolsado` | Valor desembolsado |
| `perc_retencao` | Percentual de retenção |
| `campanhas_7d` | Contagem de campanhas nos sete dias anteriores |
| `campanhas_30d` | Contagem de campanhas nos trinta dias anteriores |
| `dias_com_acionamento_30d` | Dias com ações de comunicação nos trinta dias anteriores |

As contagens históricas de campanhas consideram deduplicação por contrato, data e ação, evitando contabilizar múltiplos canais de uma mesma campanha como eventos distintos.

## 6. Separação temporal

Os dados foram divididos cronologicamente:

| Conjunto | Período | Observações |
|---|---|---:|
| Treinamento | 06/01/2020 a 27/12/2021 | 696.621 |
| Validação | 10/01/2022 a 28/02/2022 | 58.863 |
| Teste | 14/03/2022 a 11/04/2022 | 31.570 |

Foi utilizado um intervalo de segurança de 14 dias entre os conjuntos.

A separação temporal busca evitar sobreposição entre janelas futuras utilizadas na construção do indicador-alvo.

## 7. Modelagem

Foram utilizados:

- Modelo de referência (*Dummy Classifier*).
- Regressão logística.
- Calibração de probabilidades pelo método de Platt.

A calibração foi avaliada separadamente do desempenho discriminativo.

## 8. Avaliação

As principais métricas incluem:

- ROC AUC.
- PR AUC.
- Brier Score.
- Log Loss.
- Diferença entre probabilidade média prevista e taxa observada.

Também foram realizadas análises de estabilidade temporal e segmentação por características dos contratos e comunicações.

## 9. Auditorias

### Integridade do indicador-alvo

Foram examinadas 97.188 janelas futuras completas.

A reconstrução da regra original não apresentou divergências. Entretanto, a comparação com uma aproximação baseada em variações positivas entre snapshots identificou 723 divergências.

Esse resultado evidencia sensibilidade à interpretação dos valores de pagamento.

### Consistência temporal das características

Foram auditadas 97.188 observações dos conjuntos de validação e teste.

As seis características foram reconstruídas sem divergências em relação aos valores armazenados.

A auditoria não comprova a disponibilidade operacional histórica dos eventos, pois não há evidência completa dos respectivos horários de disponibilização ou ingestão.

## 10. Classificação do modelo

O modelo permanece classificado como **EXPERIMENTAL**.

A evolução para uma aplicação operacional exigiria validação da semântica do indicador-alvo, confirmação da disponibilidade temporal dos dados e novas avaliações de calibração e estabilidade.