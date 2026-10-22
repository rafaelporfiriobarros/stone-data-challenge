# Limitações e riscos — Stone Data Challenge

## 1. Objetivo

Registrar as limitações metodológicas, técnicas e operacionais identificadas durante o desenvolvimento do projeto.

A documentação dessas restrições faz parte da governança da solução e evita interpretações indevidas dos resultados.

## 2. Semântica do indicador-alvo

O indicador `target_pagamento_7d` foi construído a partir da presença de valores positivos em snapshots futuros do campo `vlr_pgto_realizado`.

Não foi comprovado que esse campo represente novos pagamentos ocorridos exclusivamente durante a janela futura de sete dias.

A comparação com uma aproximação baseada em variações positivas identificou 723 divergências em 97.188 janelas completas.

**Impacto:** as métricas do modelo se referem ao indicador implementado, e não necessariamente à ocorrência real de novos pagamentos.

**Mitigação necessária:** validar a semântica do campo com a documentação de origem e, preferencialmente, reconstruir o indicador a partir de eventos financeiros individualizados.

## 3. Calibração temporal

No conjunto de teste, a probabilidade média prevista após calibração foi de aproximadamente 54,24%, enquanto a taxa observada foi de 44,82%.

A diferença de aproximadamente 9,42 pontos percentuais indica superestimação média.

**Impacto:** as probabilidades não devem ser utilizadas diretamente como estimativas confiáveis de recebimento financeiro.

**Mitigação necessária:** investigar mudanças de distribuição, reavaliar a calibração e validar o desempenho em períodos posteriores.

## 4. Disponibilidade histórica dos dados

A auditoria temporal reconstruiu seis características em 97.188 observações, sem divergências.

Entretanto, a reconstrução baseada em datas dos eventos não comprova que as informações estivessem efetivamente disponíveis nos sistemas operacionais no momento da previsão.

**Impacto:** permanece um risco de utilização retrospectiva de informações disponibilizadas tardiamente.

**Mitigação necessária:** incorporar horários de ingestão e disponibilidade, além de testar explicitamente os limites temporais de acesso aos dados.

## 5. Interpretação das comunicações

As características relacionadas a campanhas representam histórico de ações observadas.

As associações entre comunicações e pagamentos podem refletir diferenças entre contratos, estratégias de acionamento e outros fatores não controlados.

**Impacto:** não é possível concluir que o envio de uma campanha causou aumento ou redução da probabilidade de pagamento.

**Mitigação necessária:** utilizar desenhos experimentais ou metodologias causais adequadas, com controles e hipóteses previamente definidos.

## 6. Cobertura temporal das fontes

As fontes possuem períodos de cobertura diferentes.

Por exemplo, os dados de TPV disponíveis no projeto não abrangem todo o período das observações de Machine Learning.

**Impacto:** ausência de registros em períodos não cobertos não deve ser interpretada como ausência de transações.

**Mitigação necessária:** explicitar a cobertura de cada fonte e diferenciar valores ausentes de valores iguais a zero.

## 7. Reprodutibilidade

A suíte completa depende de dados e artefatos previamente preparados no ambiente de desenvolvimento.

O repositório inclui uma demonstração sintética independente, mas ela não reproduz a distribuição estatística, o indicador-alvo ou os modelos originais.

**Impacto:** o sucesso da demonstração não comprova a reprodutibilidade integral do experimento original em um ambiente limpo.

**Mitigação necessária:** disponibilizar dados autorizados ou cenários sintéticos compatíveis com os contratos de dados necessários à execução completa.

## 8. Uso operacional

O modelo não foi validado para decisões financeiras em produção.

Não foram demonstrados, de maneira suficiente, requisitos como monitoramento operacional contínuo, validação prospectiva, gestão de mudanças e procedimentos de intervenção.

## 9. Classificação final

**Status do modelo: EXPERIMENTAL.**

Os resultados são adequados para estudo técnico e demonstração de competências em Engenharia de Dados, Analytics e Machine Learning.

Não devem ser utilizados como recomendações operacionais de crédito ou cobrança.