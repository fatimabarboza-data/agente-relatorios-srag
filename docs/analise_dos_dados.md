# Análise dos dados e decisões de tratamento

Antes de construir o agente, explorei a base de SRAG para entender o que ela permite e o que não permite
calcular. Este documento registra o que encontrei e as decisões tomadas, com os números que as justificam.

**Arquivo:** `INFLUD25_DATASUS-Versao26-06-2025` (Open DATASUS, SRAG Hospitalizado, SIVEP-Gripe)
**Tamanho:** 165.397 notificações × 194 colunas

## 1. Período coberto

| Campo | Mínimo | Máximo | Nulos |
|---|---|---|---|
| `DT_NOTIFIC` (data da notificação) | 29/12/2024 | 26/06/2025 | 0% |
| `DT_SIN_PRI` (1º sintomas) | 29/12/2024 | 25/06/2025 | 0% |

**Consequências:**
- O arquivo tem **cerca de 6 meses**, não 12. O gráfico mensal mostra os 12 meses pedidos, mas marca os
  meses de jul a nov/2024 como "fora do arquivo", em vez de desenhar barras zeradas (que sugeririam
  "zero casos").
- O dia 26/06/2025 tem só **3 registros**: é o dia da extração, ainda incompleto. A **data de referência** do
  relatório é o último dia completo (25/06/2025).

## 2. Qual data usar para contar casos

Pela data de 1º sintomas, os últimos 7 dias (19 a 25/06) somam 2.628 casos, contra 7.464 nos 7 anteriores: uma
queda de 64,8%. Pela data de notificação, a queda no mesmo período é de 35,9%. A diferença vem do atraso de
notificação: um caso entra no sistema dias depois de começarem os sintomas, então os dias mais recentes por data
de sintomas ainda estão incompletos.

Por isso, as contagens usam a **data de notificação**. Ela é estável (não muda depois de registrada) e a
série mostra o padrão esperado de rotina: segunda-feira com pico, fim de semana com queda e o feriado de
Corpus Christi (19/06/2025) com queda. O gráfico diário traz uma **média móvel de 7 dias** para separar
a tendência desse ruído.

## 3. Qualidade dos campos usados nas métricas

| Campo | Situação encontrada | Decisão |
|---|---|---|
| `EVOLUCAO` | 22,7% nulos (casos ainda em aberto) | Mortalidade calculada só sobre casos **encerrados** (cura ou óbito). |
| `UTI` | 11,5% nulos e 1.846 "ignorado" | Denominador = casos com Sim ou Não. |
| `DT_ENTUTI` | 557 datas antes dos sintomas ou depois da extração | Datas impossíveis viram nulas. |
| `DT_INTERNA` | datas de 1695 e de 2202 | Campo não usado nas métricas. |
| `VACINA_COV` | **24.575 de 45.958 bebês com menos de 1 ano** marcados como vacinados contra covid; só **25,6%** dos "Sim" têm a data da 1ª dose | Critério conservador: vacinado = "Sim" **e** data da 1ª dose registrada. |

## 4. O que a base não permite calcular

| Métrica pedida | Limitação | Aproximação adotada |
|---|---|---|
| Taxa de ocupação de UTI | A base não informa quantos leitos de UTI existem | % dos internados que foram para UTI |
| Taxa de vacinação da população | A base só tem pessoas internadas, não a população | % dos casos internados com vacina covid comprovada |

As aproximações aparecem marcadas com * no relatório, com a definição exata e os números de origem.

## 5. Dados sensíveis (LGPD)

A base contém dados pessoais e sensíveis de saúde (data de nascimento, sexo, raça/cor, escolaridade,
município, unidade de saúde, ocupação, campos de texto livre). Apliquei **minimização**: só 13 colunas
entram no banco, e nenhuma delas identifica a pessoa.

| Entra no banco | Fica de fora |
|---|---|
| datas de notificação e sintomas, UF de notificação, faixa etária (não a idade), UTI e data de entrada, evolução e data, vacina (sim/não e comprovação), classificação final | número da notificação (vira id sequencial), data de nascimento, idade exata, sexo, raça, escolaridade, município, unidade de saúde, ocupação, textos livres, lotes de vacina |

Além disso, o LLM **nunca** recebe linhas da base: só os indicadores agregados.
