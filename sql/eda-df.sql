create table df(
	contrato_id varchar,
	dt_ref_portfolio date,
	nr_documento varchar ,
	status_contrato varchar ,
	dt_desembolso date,
	dt_vencimento date,
	prazo varchar ,
	vlr_desembolsado numeric ,
	vlr_tarifa numeric ,
	juros_mes numeric ,	
	juros_diario numeric ,	
	perc_retencao numeric ,	
	vlr_pgto_realizado numeric ,	
	vlr_pgto_esperado numeric ,	
	vlr_saldo_devedor numeric ,
	vlr_saldo_devedor_esperado numeric ,	
	dsp numeric ,
	dspp numeric ,
	flag_transacao numeric ,
	qtd_meses_pagto numeric ,
	tipo_empresa varchar ,
	cidade varchar , 
	estado varchar ,
	subsegmento varchar,
	segmento varchar ,
	data_acao date,
	tipo_acao varchar ,
	acao varchar ,
	status varchar 
);

-------------------- SELECT -------------------- 
-- 1. Liste todas as colunas da tabela df.

select * from df;

-- 2. Liste os contratos da tabela df.

select contrato_id from df;

-- 3. Liste os contratos e números de documentos dos clientes.

select contrato_id, nr_documento from df;

-------------------- DISTINCT --------------------

-- Seleção de uma coluna sem DISTINCT		
-- 4. Liste os segmentos que constam na tabela df.

select segmento from df;

-- Seleção de uma coluna com DISTINCT
-- 5. Liste os segmentos distintos que constam na tabela df.

select distinct segmento from df;

-- 6. Liste os segmentos e subsegmentos distintos que constam na tabela df.

select distinct segmento, subsegmento from df;

-------------------- WHERE --------------------

-- 7. Liste os contratos (contrato_id) que moram no estado de São Paulo?

select contrato_id, estado from df
where estado = 'SP';

-- 8. Liste os contratos (contrato_id) que moram no estado de São Paulo ou Rio de Janeiro?

select contrato_id, estado from df
where estado = 'SP' or estado = 'RJ';

-- 9. Liste os contratos (contrato_id) que moram no estado de São Paulo ou Rio de Janeiro, 
-- e que tenham data de desembolso (dt_desembolso) mais de 3 anos?

-- versao 1
select contrato_id, estado, dt_desembolso from df
where (estado = 'SP' or estado = 'RJ') and dt_desembolso < '2020-11-24';

-- versao 2
select contrato_id, estado, dt_desembolso from df
where (estado = 'SP' or estado = 'RJ') and dt_desembolso < '20201124';

-------------------- ORDER BY --------------------

-- 10. Liste os contratos e o valores desembolsados (vlr_desembolsado) 
-- da tabela df na ordem crescente com base no valor desembolsado (vlr_desembolsado).

select contrato_id, vlr_desembolsado from df
order by vlr_desembolsado asc;

-- 11. Liste os estados distintos da tabela df na ordem crescente.

select distinct estado from df
order by estado asc;


-------------------- LIMIT --------------------

-- 12. Liste os 10 primeiras linhas da tabela df.

select * from df limit 10;

-- 13. Liste os 10 valores de saldo devedor (vlr_saldo_devedor) mais altos da tabela df.

select * from df order by vlr_saldo_devedor desc limit 10;





-------------------- OPERADORES ARITMÉTICOS --------------------

-- 14. Crie uma coluna contendo a diferença de meses entre a data de desembolso e a data de ação?

-- opçao 1
select abs(dt_desembolso - data_acao) / 30 as meses_ate_primeira_acao
from df

-- opção 2
select abs(dt_desembolso - data_acao) / 30 as "meses ate primeira acao"
from df

-- 15. Liste os 10 contratos com mais meses até a primeira ação?

select contrato_id, abs(dt_desembolso - data_acao) / 30 as meses_ate_primeira_acao
from df order by meses_ate_primeira_acao desc limit 10;

-- 16. Crie uma coluna cliente_completo contendo o contrato_id + nr_documento

select contrato_id || ' ' || nr_documento as cliente_completo from df;








