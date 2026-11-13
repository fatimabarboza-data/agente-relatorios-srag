# Relatório de SRAG

Dados até **25/06/2025** · gerado em 13/11/2026 15:10 · execução `53163b537fd5`

> Relatório gerado automaticamente por um agente de IA como prova de conceito. Não substitui boletins oficiais nem avaliação de profissionais de saúde, e não contém orientação médica individual.

## Resumo executivo

Os dados até 25/06/2025 indicam estabilidade na tendência de 30 dias (+0,36%) e queda acentuada na comparação semanal (-35,89%), embora o efeito de notificações atrasadas e menor fluxo em fins de semana exija cautela na interpretação da redução recente. A letalidade hospitalar por SRAG situa-se em 8,48%, enquanto 26,95% dos internados com informação de UTI preenchida necessitaram de terapia intensiva (proxy, não taxa de ocupação de leitos). Entre os casos com status vacinal informado, 46,25% possuíam registro de primeira dose contra covid-19 (proxy, não cobertura populacional).

## Métricas

| Métrica | Valor | Numerador | Denominador |
|---|---:|---:|---:|
| Taxa de aumento de casos (7 dias) | −35,9% | 6.698 | 10.448 |
| Taxa de aumento de casos (30 dias) | +0,4% | 46.845 | 46.678 |
| Taxa de mortalidade (letalidade hospitalar por SRAG) | 8,5% | 2.029 | 23.927 |
| Taxa de ocupação de UTI (proxy: % de internados que foram para UTI) | 26,9% | 10.673 | 39.608 |
| Taxa de vacinação contra covid-19 (proxy: % dos casos com vacina comprovada) | 46,2% | 21.399 | 46.264 |

## Análise

- **Taxa de aumento de casos (7 dias)**: A variação de -35,89% (6.698 vs 10.448 casos) sugere redução importante nas notificações da semana mais recente. Contudo, os registros mais recentes ainda recebem notificações atrasadas e fins de semana/feriados tendem a reduzir o fluxo de notificação; portanto, não se deve afirmar queda sustentada de casos sem consolidação das próximas semanas.
- **Taxa de aumento de casos (30 dias)**: A variação de +0,36% (46.845 vs 46.678 casos) indica estabilidade no volume de notificações ao longo do último mês, o que contrasta com a queda semanal e reforça a necessidade de aguardar a consolidação dos dados recentes antes de inferir mudança de tendência.
- **Taxa de mortalidade (letalidade hospitalar por SRAG)**: A letalidade hospitalar de 8,48% (2.029 óbitos em 23.927 casos com evolução conhecida) reflete a gravidade dos casos notificados no período. O indicador considera apenas casos com desfecho informado (cura ou óbito), podendo subestimar a letalidade real se houver grande proporção de evoluções em aberto.
- **Taxa de ocupação de UTI (proxy: % de internados que foram para UTI)**: O proxy de 26,95% (10.673 de 39.608 internados com informação de UTI preenchida) representa a proporção de hospitalizados que necessitaram de terapia intensiva, não a taxa de ocupação de leitos de UTI da rede. A métrica depende do preenchimento do campo UTI (Sim/Não) e pode variar com a completude do dado.
- **Taxa de vacinação contra covid-19 (proxy: % dos casos com vacina comprovada)**: Entre os casos com status vacinal informado (Sim/Não), 46,25% (21.399 de 46.264) apresentavam registro de primeira dose contra covid-19. Trata-se de proxy da situação vacinal dos casos notificados, não da cobertura vacinal da população geral, e está sujeito a viés de notificação e completude do campo vacina.

## Gráficos

![Casos diários](casos_diarios_30d.png)

![Casos mensais](casos_mensais_12m.png)

## Contexto das notícias

As notícias disponíveis referem-se a novembro de 2026 [1-12], período posterior à data de referência dos dados (junho de 2025). Elas descrevem sinais de crescimento de SRAG e covid-19 naquele momento, o que não se sobrepõe ao cenário de estabilidade/queda observado nos indicadores de junho de 2025. A discrepância temporal deve ser considerada ao contextualizar o relatório.

1. [Casos graves de Covid-19 dão sinal de crescimento no Brasil, aponta Fiocruz](https://news.google.com/rss/articles/CBMirwFBVV95cUxNYkxXVDYydDF6MklRNTlnSWNqVkFHcDBqdDhDdzhBSHhUb0FpWk5WalRWOUYwVlVITm9pR3ZsVS1YVGpDbWN5M3I0UDV1ZVFYdlQwUGY3OEtSV09CZHJCajhJR2Z6UnBUQkFnVkdxLVktMEtHajFfTHA1OEVUREhhbEE0TlQzUTM3S2kzalY0WEJkT25tR2drVEhyTlZXcmJyYzlRM1JkdEVQTm9HX1BB?oc=5) - CNN Brasil, 13/11/2026
2. [Casos de Covid-19 apresentam aumento no Brasil, aponta boletim da Fiocruz](https://news.google.com/rss/articles/CBMinwFBVV95cUxQN3pabm9mWmNZQlVrS1p3SjZZUFJoMzhqczc1SWFQSFU3NEJ1cjNFclo1ZVhTR0t2eVpDY1MwMjdWNWExMlhmRlp5RmdSVllnRHBJYXM3T2xPRnVnbHh5WFJKZDVmc3ljT1V5eXVoVlRwcFJkVTh3X1JzckpwSTFWNzh2UDZieldUZGRGcGh5Y0RoejRsUzFzUXpMQTQxRlU?oc=5) - Fala Matão, 13/11/2026
3. [Fiocruz: aumentam casos de síndrome respiratória aguda por covid-19](https://news.google.com/rss/articles/CBMivgFBVV95cUxNZy1seFVIRUdYeHNfbWg3SjVleXhPZEp0MWxxeUdzV3FFRV9SSDdSOFR1Q0l6bWtvd3pneEJHbk9Wa3hwTFZ3TVB1UmVPMEw2MlVYMEEtbVVsd05EM0lGdDZLVThqTjU0V29oUkM4a3B5U1VpWkpQVjlfUkFrR0Z5a1JBdTJla1NSTU5acDRoN1lvSEkzSC01ZGU2UjF6SDJrNjBGWFZHWmprVERBYW1idFd5MWxGS1hidlkwYkp3?oc=5) - Agência Brasil, 12/11/2026
4. [Aumento de Casos de SRAG por Covid-19 no Brasil em Novembro](https://news.google.com/rss/articles/CBMijgFBVV95cUxQMDVIME9RR0NWZmZxR0llLVJRWFBtdUN1NnJYc1gxclZEN3NxOEVRRDJ3a1h4QjZtSk9wLVBsRXlMMTdfRVhzWExHd3pMdWxUTTk3Q1hvZU1PUFY5dTFqMXRaUXJKWV9BR3E0RHUzaUlzbUlNMlNIbWhsRExqLVFYcWFrSDdPOF9QdTR5QktB?oc=5) - Metrô News Jornal, 12/11/2026
5. [Acre segue fora dos grupos de alerta para SRAG enquanto Fiocruz aponta queda de casos no país](https://news.google.com/rss/articles/CBMixwFBVV95cUxPT0VkcG9taER6bUd3QmVBbnNYeWlLTzlTR2JDOTJaT3VjV2VFdWZ3TjRYWkRyWkdfeFlHcDZaUnlwZE9tanlJa2pZenVPV0t0TUlTZU8yNXdrbmd2T0pnTHhyYXpjdldaUllzMW5iRFdLc3RTRXlWc0Jhb1RkQ2lrb05Icll1TUV0MWtpa1l1aUo1ci02VDloMU56b3g5SjdXU1hQM0dDWDdka2E0b1lFc0tJM3ZudDk5cURmZnpLcnRIMHZuZnE4?oc=5) - Portal Acre, 12/11/2026
6. [Fiocruz aponta alta de casos graves de covid-19 no início de novembro](https://news.google.com/rss/articles/CBMiqgFBVV95cUxPRTltbFNGRER6eU9vUWI5Tl9DUldpREtPRWlWWDJkbUVCVkstaDBuRkdQWWJvRWU4ZTE1d0F0c3FLQWtZcVNaWHVDV2ZSaGJEZF9HaTIzQjU3bE8xcy1uYjZTZW85Ynk3bUdqdl9WVFhrMWFiZWFNajF3UjNlVXNvWm5MbHVHZDFwR3lBNHgtTU1kN2FfR0lrVVBvTThBTHhKb2pkNHBfSEdpQQ?oc=5) - TODODIA, 12/11/2026
7. [Fiocruz aponta alta de casos graves de covid-19 no Brasil](https://news.google.com/rss/articles/CBMiqgFBVV95cUxOS2xsX0hXV1lJWkdDbWhzNHJmWWNHN05UU2ozT0w3R2J0SEluWDN4cE92Q3NPT2J1bV9JVmI0N2FzR2VZZloweWs5NHI2MmhWUlZoOU84VHBzYkREX3NXcXRoQkl2cGNqREtEaDlnY3FkZEUxbGdYS3M5ckNvLUFZYlpqZm5jNUJtOFJpazcxc3FhQnc1QlpPQnBKdEdvSUVtRGxlYXlLUDIxZ9IBrwFBVV95cUxQNV93OTluV1VqMFRWb0N1T0FsRmFtQUFhbFlRbUllYjVNczBUd09iNUpRZUpYTEVnbmkzQ001ZklKYlQ1Q2VxZXpYS3JJMENLNkJvTTN2cnBKckQ0UmlpbVFLNTMwaUxjWW1LSmF4N3Y5WWlicV9OUGVLYnBVSll2alpmNGxOdHhDV25RQnAyaHJrSzUxV2RvQTh3NFlPaWZpV2NCV3lYM0xHcERKYWFj?oc=5) - Portal Piauí Hoje, 12/11/2026
8. [Casos de Covid-19 voltam a crescer no Rio, aponta Fiocruz](https://news.google.com/rss/articles/CBMimgFBVV95cUxQLW9hZ2F4VEk0LUNZbW5xVmR6V3ZjWnMwVDU0M1ltOXp4Y0k5WXVXNllTbGhhT1h3Q0FST0JLbWhCbGtJNFRSYjBTR1JEV2dpMEtLMmhqOTJXNWJLY0Q5TXQ3X015aC0tc25GSF9SS1dWR1RBMXgzWDI3UlQ3S3VlemxhZFc4eFF3eHhYcE1COXJ5YUhpM2gyVEtB?oc=5) - A Tribuna RJ, 12/11/2026
9. [Casos graves de Covid-19 voltam a subir em seis estados, indica boletim InfoGripe](https://news.google.com/rss/articles/CBMi4gFBVV95cUxNU3pmcDVZeXBMR0FPcmlSMHAxa0oxb0xFejA3cEtPdGdGYmxxTFd3OW5oU0lmYzlZalA5WFBhVEpjREs5dlJBWWZjTl9RZjRFS1VXNTBQZ0p2Y1A0QkpzM1FLLXppY053Q1JQZjJUeXVtRUNib1l4Y0xiOFdMaVdRZFVRa01YYW91NHVGb1pKNHFUck5mV2xscXBBRGhaaHZTR05uNjcxaDdnTmdWTXV6OUxBTDNfVWZYbDFVak5SVFE2b2Nhb2Y4N2JnU2tmaWlNOWZScTNLUG5YQ3lpOE9yYkRn?oc=5) - Correio do Povo, 13/11/2026
10. [Alta de casos de SRAG no boletim InfoGripe motiva alerta de pneumologista da Santa Casa de Mauá](https://news.google.com/rss/articles/CBMif0FVX3lxTE8yWlByMGZYSXN1NnFfSExxYVU0b1FuMkNLc1k3WEpaVUlVV1Y4UkI1MlpwUHBMQmh4X0ZrNEF2U0RqYU5BTTAzSVltUTB4UktPV3NHV2xmQUZmYVFmTE9RVl9RdmJYV3FpWUlWcmtPeW9ZUWs5d0pxN2E3TzNVeE0?oc=5) - ABC Agora, 12/11/2026
11. [Casos de Síndrome Respiratória Grave (SRAG) devem aumentar, diz boletim da Fiocruz](https://news.google.com/rss/articles/CBMi5gFBVV95cUxNS29MdUJPTXdvLXZZZUdnSDM0RGpXSzd1S3ZNTzJEeWJVMDlpQ21QeFVlVmZwSm5PSl9FbTNUVnpYVE82czZwbWduXzAxTHRPM2tId1lrS1AtUFhDU1RsVmozMnlrVDdzaGh0N0lzRnVYY0I2RkFOY21yaEx3NVJVT0FOcjNtZXhVZURaRVVCZG1uUEw4czdLcDkxbVRCRXlvR2l1cVFzQlpSZDQzVFZROTZsRFQwalBXcnZwVVlTVGl0R3JjZ3MxR2Y4WDJYN2d6aFdFUTFZYWFJSUlONDFNZmhyRC04dw?oc=5) - Diario de Pernambuco, 11/11/2026
12. [InfoGripe: casos de SRAG por metapneumovírus, rinovírus e Covid-19 crescem no país](https://news.google.com/rss/articles/CBMiygFBVV95cUxQM1U1VzYzemh2R3JTem8yTVNxV09rRGV3LVBHQ1RLaW5qX0ZSZGdqUXh2UTlqRFFDMEdMeGFtbUR6SGJxQkdlTnNQTzk1enJ6Y0tPLWdvNDlyTHkycVN0bkZMX3oyMXB2Rkd2WXdUODFKYTRpc1JMamJuZTJCX3BjaW80OWNlQjBGRkZOS3ZKQ0JYOWNNUUFqNGpQY0hTQUJ2M284Yk9CdjFUNVlXMUNoS1NTYjNVendHUzlKZUtaMkpHQzY5dzBqc0VB?oc=5) - Portal do Marcos Santos, 07/11/2026

## Pontos de atenção

- Aguardar consolidação das notificações das semanas mais recentes antes de confirmar tendência de queda, dado o atraso habitual e efeito de fim de semana.
- Monitorar a completude dos campos de evolução (cura/óbito), UTI e vacinação para reduzir viés nos proxies de letalidade, necessidade de terapia intensiva e situação vacinal dos casos.
- Acompanhar a tendência de 30 dias nas próximas atualizações para distinguir flutuação de notificação de mudança epidemiológica real.
- Considerar a sazonalidade de vírus respiratórios e a circulação de múltiplos agentes (covid-19, influenza, vírus sincicial, metapneumovírus, rinovírus) na interpretação do volume de SRAG.

## Limitações

- O arquivo disponibilizado cobre de 29/12/2024 a 26/06/2025; o gráfico de 12 meses mostra os meses anteriores como fora do arquivo.
- Ocupação de UTI é aproximada pela proporção de internados que foram para UTI: a base não informa a quantidade de leitos disponíveis.
- Vacinação é aproximada pela proporção de casos internados com vacina contra covid-19 comprovada (data da 1ª dose registrada); não é a cobertura vacinal da população.
- Mortalidade é a letalidade hospitalar: óbitos por SRAG entre casos já encerrados. Casos ainda em aberto ficam fora do cálculo.
- Os últimos dias recebem notificações com atraso; quedas recentes tendem a ser revistas para cima.
