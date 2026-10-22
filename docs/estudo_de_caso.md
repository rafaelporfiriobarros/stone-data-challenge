# Estudo de caso — Stone Data Challenge

## 1. Problema

Dados financeiros e operacionais frequentemente estão distribuídos em diferentes fontes, com granularidades, períodos e regras de negócio distintos.

O desafio abordado neste projeto foi transformar informações sobre contratos, pagamentos, TPV e comunicações em uma base analítica consistente, capaz de sustentar análises e experimentos preditivos.

## 2. Abordagem

O desenvolvimento foi organizado em etapas:

1. Inspeção das fontes e análise dos esquemas.
2. Ingestão e estruturação em camadas Bronze, Silver e Gold.
3. Verificações de qualidade e reconciliação.
4. Construção de uma base analítica de observações semanais.
5. Separação temporal para experimentação de Machine Learning.
6. Treinamento e calibração de modelos.
7. Avaliação de desempenho e estabilidade.
8. Auditoria do indicador-alvo e das features.
9. Documentação de riscos e governança.
10. Criação de uma demonstração sintética com integração contínua.

## 3. Principais decisões técnicas

### Separação das camadas de dados

A arquitetura Bronze, Silver e Gold permite distinguir ingestão, tratamento e consumo analítico.

Essa organização facilita a investigação de divergências e a aplicação de testes em pontos específicos do fluxo.

### Definição da granularidade

A modelagem considera explicitamente a chave de cada tabela, evitando que relações entre contratos, transações e comunicações produzam contagens incorretas.

### Validação temporal

A separação dos dados respeita períodos distintos de treinamento, validação e teste, com um intervalo de segurança entre os conjuntos.

Essa decisão reduz o risco de sobreposição das janelas utilizadas na construção do indicador-alvo.

### Avaliação além da acurácia

O projeto utiliza métricas de discriminação e de qualidade probabilística, incluindo ROC AUC, PR AUC e Brier Score.

Também analisa diferenças entre probabilidades previstas e taxas observadas.

### Auditoria da definição do indicador-alvo

Uma verificação específica comparou o indicador original com uma aproximação alternativa baseada em variações positivas entre snapshots.

Foram encontradas 723 divergências em 97.188 janelas completas analisadas.

Esse resultado reforça a necessidade de validar a semântica dos campos antes de utilizar o indicador em decisões financeiras.

## 4. Resultados

A solução produziu tabelas analíticas, uma base de observações semanais, modelos experimentais e relatórios de avaliação.

A regressão logística apresentou ROC AUC de aproximadamente 0,785 no teste.

Entretanto, a probabilidade média prevista após calibração permaneceu superior à taxa observada, indicando um problema relevante de calibração temporal.

A auditoria das features não encontrou divergências nas seis características reconstruídas para as 97.188 observações verificadas.

## 5. Engenharia e reprodutibilidade

A suíte completa registrou 126 testes aprovados no ambiente local.

Também foi criada uma demonstração independente com dados sintéticos, executada com sucesso em integração contínua no GitHub Actions.

Essa separação permite demonstrar práticas de engenharia sem distribuir os dados originais.

## 6. Limitações identificadas

O projeto não comprova que os valores positivos dos snapshots representem novos pagamentos realizados na janela futura.

Também não comprova disponibilidade operacional histórica integral dos dados utilizados nas features.

As relações observadas entre campanhas e pagamentos não devem ser interpretadas como efeitos causais.

Por essas razões, o modelo permanece experimental.

## 7. Aprendizados

O principal aprendizado foi a importância de combinar modelagem, qualidade de dados, avaliação temporal e governança.

Uma métrica preditiva isolada não é suficiente para justificar o uso operacional de um modelo.

É necessário compreender o significado dos dados, testar as transformações, investigar a estabilidade das previsões e documentar os riscos.

## 8. Próximos passos técnicos

Para evoluir a solução, seriam necessárias ações como:

- Validar com a área de negócio a semântica dos campos de pagamento.
- Construir um indicador-alvo baseado em eventos financeiros comprovados.
- Registrar a disponibilidade operacional dos dados e seus horários de ingestão.
- Reavaliar a calibração em períodos futuros.
- Investigar mudanças de distribuição e desempenho por segmento.
- Ampliar a reprodutibilidade do pipeline original com dados autorizados ou simulados.

## Conclusão

O Stone Data Challenge é um projeto de portfólio que demonstra a construção e a avaliação crítica de uma solução analítica de ponta a ponta.

Seu diferencial não está apenas no treinamento de um modelo, mas também na investigação dos problemas que podem comprometer a confiabilidade de seus resultados.