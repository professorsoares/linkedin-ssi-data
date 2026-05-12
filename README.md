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

# se quiser forçar sobrescrever o arquivo do dia: 
python scrape_ssi.py --force
```

Abra o arquivo gerado no browser:

```bash
# Windows
start dashboard.html

# macOS
open dashboard.html
```

### Adicionar uma nova coleta

**Opção A — automático (recomendado)**

Instale o Playwright uma única vez:

```bash
pip install playwright
playwright install chromium
```

Na primeira execução, um browser abrirá para você fazer login no LinkedIn. A sessão fica salva localmente para os próximos usos:

```bash
python scrape_ssi.py

# se quiser forçar sobrescrever o arquivo do dia: 
python scrape_ssi.py --force
```

O script coleta os dados, gera o CSV em `data/` e atualiza o dashboard automaticamente.

| Flag | Descrição |
|---|---|
| _(nenhuma)_ | Coleta normal usando sessão salva |
| `--login` | Força novo login (use se a sessão expirar) |
| `--debug` | Salva screenshot e JSON bruto em `.debug/` para diagnóstico |

> **Nota:** Na primeira execução ou após um `--debug`, pode ser necessário ajustar os
> caminhos de campos em `scrape_ssi.py` → `extract_from_api()` de acordo com a
> estrutura real da API retornada pelo LinkedIn (ela pode variar por conta).

**Opção B — manual**

1. Acesse [LinkedIn SSI](https://www.linkedin.com/sales/ssi) e extraia os dados manualmente
2. Salve o arquivo em `data/ssi_YYYY-MM-DD.csv` no formato descrito abaixo
3. Rode `python generate_dashboard.py`

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
- Fonte dos dados: 




## Inicio


 python -m venv .venvSSIData

.venvSSIData\Scripts\activate


.venvSSIData\Scripts\python.exe -m pip install --upgrade pip
