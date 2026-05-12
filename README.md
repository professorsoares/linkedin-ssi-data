# linkedin-ssi-data

Coleta e visualização do LinkedIn Social Selling Index (SSI) ao longo do tempo.

## Dashboard

O script `generate_dashboard.py` lê todos os CSVs da pasta `data/` e gera um `dashboard.html` autocontido com os seguintes gráficos:

- **Gauge** — score SSI atual
- **Donut** — distribuição dos 4 componentes
- **Radar** — você vs média do setor vs média da rede
- **Barras** — comparativo por componente
- **Linha temporal** — evolução do SSI e componentes ao longo das coletas

### Pré-requisitos

Python 3.9 ou superior. Nenhuma dependência externa — usa apenas a biblioteca padrão.

### Como rodar

```bash
python generate_dashboard.py
```

Abra o arquivo gerado no browser:

```bash
# Windows
start dashboard.html

# macOS
open dashboard.html
```

### Adicionar uma nova coleta

1. Exporte os dados do [LinkedIn SSI](https://www.linkedin.com/sales/ssi) para um CSV
2. Salve o arquivo em `data/` com o nome no formato `ssi_YYYY-MM-DD.csv`
3. Rode `python generate_dashboard.py` novamente

O dashboard atualiza automaticamente com o novo snapshot e o inclui na série temporal.

### Formato do CSV

Separador `;`, encoding `UTF-8 BOM`. Colunas esperadas:

| Coluna | Descrição |
|---|---|
| `data_referencia` | Data da coleta (`YYYY-MM-DD`) |
| `campo` | Nome do campo SSI |
| `secao` | Seção da tela do LinkedIn |
| `valor_numerico` | Valor numérico (ponto ou vírgula como decimal) |

---

## Notas

- Os dados são gerados manualmente a partir da tela do LinkedIn SSI com auxílio do ChatGPT: https://chatgpt.com/c/69fa7e50-7d90-832d-99ab-039cf0f0f827
- Fonte dos dados: https://www.linkedin.com/sales/ssi



## Inicio


 python -m venv .venvSSIData

.venvSSIData\Scripts\activate


.venvSSIData\Scripts\python.exe -m pip install --upgrade pip
