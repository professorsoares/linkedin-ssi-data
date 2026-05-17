# linkedin-ssi-data

Coleta e visualização do LinkedIn Social Selling Index (SSI) e das solicitações de serviço do LinkedIn Service Marketplace.

---

## SSI — Social Selling Index

### Dashboard

O script `generate_dashboard.py` lê todos os CSVs da pasta `ssi/data/` e gera um `dashboard.html` autocontido com os seguintes gráficos:

- **Gauge** — score SSI atual
- **Donut** — distribuição dos 4 componentes
- **Radar** — você vs média do setor vs média da rede
- **Barras** — comparativo por componente
- **Linha temporal** — evolução do SSI e componentes ao longo das coletas

### Pré-requisitos

Python 3.9 ou superior. Para coleta automática, instale o Playwright uma única vez:

```bash
pip install playwright
playwright install chromium
```

### Como rodar

Na primeira execução, um browser abrirá para você fazer login no LinkedIn. A sessão fica salva localmente para os próximos usos.

```bash
python ssi/scrape_ssi.py
```

Em seguida, gere o dashboard:

```bash
python generate_dashboard.py
```

Ou execute o pipeline completo (coleta → dashboard → commit git):

```bash
python run_daily.py
```

| Flag | Descrição |
|---|---|
| _(nenhuma)_ | Coleta normal usando sessão salva |
| `--login` | Força novo login (use se a sessão expirar) |
| `--force` | Sobrescreve o CSV do dia se já existir |
| `--debug` | Salva screenshot e JSON bruto em `.debug/` para diagnóstico |

Os CSVs são salvos em `ssi/data/ssi_YYYY-MM-DD.csv`.

### Formato do CSV

Separador `;`, encoding `UTF-8 BOM`. Colunas esperadas:

| Coluna | Descrição |
|---|---|
| `data_referencia` | Data da coleta (`YYYY-MM-DD`) |
| `secao` | Seção da tela do LinkedIn |
| `campo` | Nome do campo SSI |
| `valor_numerico` | Valor numérico (ponto ou vírgula como decimal) |

---

## Service Marketplace — Solicitações de Serviço

Captura as solicitações abertas na página de provider do LinkedIn Service Marketplace e salva um JSON completo por solicitante (dados da solicitação + informações de contato do perfil).

### Como rodar

```bash
python requests/scrape_requests.py
```

O script executa duas etapas em sequência dentro da mesma sessão de browser:

1. **Coleta de solicitações** — percorre a lista em `linkedin.com/service-marketplace/provider/requests/`, clica em cada item e extrai os dados do painel de detalhe
2. **Contatos** — visita o overlay de informações de contato de cada solicitante (`/overlay/contact-info/`) e inclui os dados disponíveis no mesmo JSON

| Flag | Descrição |
|---|---|
| _(nenhuma)_ | Coleta normal usando sessão salva |
| `--login` | Força novo login (use se a sessão expirar) |
| `--force` | Sobrescreve os JSONs do dia se já existirem |
| `--debug` | Salva screenshots e HTML em `.debug/` para diagnóstico |

Os JSONs são salvos em `requests/data/YYYY-MM-DD_NN_<slug-do-perfil>.json`.

### Formato do JSON

```json
{
  "data_referencia": "2026-05-16",
  "hora_referencia": "10:30",
  "titulo_projeto": "Coaching de desenvolvimento de carreira",
  "localizacao": "São Paulo, São Paulo",
  "tempo_publicado": "Há 1 d",
  "solicitante": {
    "nome": "Stefany Santos",
    "perfil_url": "https://www.linkedin.com/in/santosstefany",
    "grau_conexao": "2º",
    "subtitulo": "Analista de Produtos | UX Design | ...",
    "conexoes_compartilhadas": "4 conexões compartilhadas"
  },
  "detalhes_projeto": [
    { "pergunta": "Como seu coach pode ajudar você?", "resposta": "Encontrar emprego" }
  ],
  "contato": [
    { "tipo": "E-mail", "valor": "exemplo@gmail.com", "url": "mailto:exemplo@gmail.com" },
    { "tipo": "Data de nascimento", "valor": "30 de maio", "url": null }
  ],
  "resposta": null,
  "fonte": "LinkedIn Service Marketplace / scrape_requests.py"
}
```

> O campo `contato` contém apenas as informações que o solicitante tornou públicas — pode ter mais ou menos campos dependendo do perfil.  
> O campo `resposta` fica `null` e pode ser preenchido posteriormente com a proposta gerada.

### Atualizar contatos de JSONs existentes

Caso um JSON já salvo não tenha informações de contato (campo `contato: null`), use o script autônomo:

```bash
python requests/scrape_contact_info.py
```

| Flag | Descrição |
|---|---|
| _(nenhuma)_ | Processa somente os JSONs com `contato: null` |
| `--force` | Reprocessa todos os JSONs, sobrescrevendo contatos existentes |
| `--debug` | Salva screenshots e HTML em `.debug/` |

---

## Estrutura de pastas

```
linkedin-ssi-data/
├── ssi/
│   ├── scrape_ssi.py          ← coleta SSI
│   └── data/
│       └── ssi_YYYY-MM-DD.csv
├── requests/
│   ├── scrape_requests.py     ← coleta solicitações + contatos
│   ├── scrape_contact_info.py ← atualiza contatos retroativamente
│   └── data/
│       └── YYYY-MM-DD_NN_<slug>.json
├── generate_dashboard.py      ← gera dashboard.html a partir dos CSVs
└── run_daily.py               ← pipeline completo do SSI (coleta → dashboard → commit)
```

---

## Configuração inicial

```bash
python -m venv .venvSSIData

.venvSSIData\Scripts\activate

python -m pip install --upgrade pip

pip install playwright

playwright install chromium
```
