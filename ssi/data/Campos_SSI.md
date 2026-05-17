# Campos SSI

Arquivo de referência: `ssi_2026-04-27.csv`  
Fonte: imagem do painel **Seu Social Selling Index** do LinkedIn.  
Data/hora visível na imagem: **27/04/2026 às 13:06**.  
Data normalizada usada no nome do arquivo: **2026-04-27**.

## Estrutura do CSV

| Coluna | Descrição | Exemplo |
|---|---|---|
| `data_referencia` | Data identificada na imagem, convertida para o padrão ISO `AAAA-MM-DD`. | `2026-04-27` |
| `hora_referencia` | Hora visível na imagem. | `13:06` |
| `secao` | Bloco visual de onde o dado foi extraído. | `Componentes da pontuação` |
| `campo` | Nome do indicador, métrica ou informação extraída. | `Social Selling Index atual` |
| `valor_original` | Valor exatamente interpretado a partir da imagem, preservando vírgula decimal e textos. | `20,973` |
| `unidade` | Unidade de medida quando aplicável. | `pontos`, `%` |
| `valor_numerico` | Valor numérico normalizado para análise, usando ponto como separador decimal. Fica vazio quando o valor é textual. | `20.973` |
| `escala` | Escala de leitura do indicador quando identificável. | `0-100`, `0-25`, `percentual/ranking` |
| `observacao` | Contexto adicional para validação e interpretação. | `Pontuação principal exibida como 53 de 100.` |
| `fonte` | Origem dos dados extraídos. | `Imagem LinkedIn SSI` |

## Campos extraídos

### Social Selling Index atual
Pontuação geral do SSI exibida no painel principal. Na imagem, o valor aparece como **53 de 100**.

### Classificação SSI do setor
Ranking relativo do perfil em comparação com profissionais do mesmo setor. Na imagem, aparece como **Primeiros 10%**.

### Classificação SSI da rede
Ranking relativo do perfil em comparação com pessoas da rede do perfil. Na imagem, aparece como **Primeiros 12%**.

### Estabelecer sua marca profissional
Primeiro componente da pontuação SSI. Na imagem, aparece como **20,973** em uma escala visual de até 25 pontos.

### Localizar as pessoas certas
Segundo componente da pontuação SSI. Na imagem, aparece como **6,38** em uma escala visual de até 25 pontos.

### Interagir oferecendo insights
Terceiro componente da pontuação SSI. Na imagem, aparece como **10,25** em uma escala visual de até 25 pontos.

### Criar relacionamentos
Quarto componente da pontuação SSI. Na imagem, aparece como **15** em uma escala visual de até 25 pontos.

### Setor de referência
Setor usado pelo LinkedIn para comparação: **Atividades de consultoria em gestão empresarial**.

### SSI médio do setor
Pontuação média dos profissionais de vendas no setor informado. Na imagem, aparece como **35 de 100**.

### Posição no setor
Confirmação da posição relativa no setor: **Primeiros 10%**.

### Variação semanal no setor
Status exibido no bloco do setor: **Sem alterações na última semana**.

### SSI médio da rede
Pontuação média das pessoas da rede do perfil. Na imagem, aparece como **36 de 100**.

### Posição na rede
Confirmação da posição relativa na rede: **Primeiros 12%**.

### Variação semanal na rede
Status exibido no bloco da rede: **Sem alterações na última semana**.

### Chamada Sales Navigator
Mensagem complementar exibida no rodapé: **Encontre os decisores certos e encurte seu ciclo de vendas com o LinkedIn Sales Navigator.**

## Observações de validação

- A soma dos quatro componentes extraídos é **52,603**, enquanto o painel arredonda/exibe o SSI atual como **53 de 100**.
- O CSV usa separador `;`, mais adequado para abertura no Excel em configuração regional brasileira.
- A coluna `valor_original` preserva os formatos vistos na imagem; a coluna `valor_numerico` facilita análises posteriores.
