# Meta Ads MCP Server

Este projeto implementa um servidor **MCP (Model Context Protocol)** para integração com a API de Marketing da Meta (Facebook Ads). Ele permite que assistentes de IA e outras ferramentas compatíveis com MCP interajam diretamente com contas de anúncios para extrair relatórios, estruturas de campanhas, criativos e métricas detalhadas.

## 🚀 Funcionalidades

O servidor expõe diversas ferramentas poderosas para análise e gestão de anúncios:

*   **`meta_list_clients`**: Lista os clientes e IDs de conta configurados.
*   **`meta_get_structure`**: Navegação hierárquica (Drill-down). Lista Campanhas de uma conta ou Conjuntos de Anúncios e Anúncios de uma Campanha.
*   **`meta_get_analytics`**: Relatórios analíticos completos (Spend, ROAS, CPA, CTR, etc.) com suporte a quebra por dia e níveis (Campanha, AdSet, Ad). Inclui links de visualização de imagens para anúncios.
*   **`meta_get_ad_creative_details`**: Detalhes do criativo (Imagem, Título, Texto/Copy, CTA) de um anúncio específico.
*   **`meta_get_account_balance`**: Verifica saldo da conta, valor gasto, limite de gastos (spend cap) e status da conta.
*   **`meta_get_demographics`**: Análise demográfica (Idade e Gênero) e por Plataforma (Instagram vs Facebook).
*   **`meta_compare_performance`**: Comparativo lado a lado de múltiplos IDs (Campanhas, AdSets, etc.).
*   **`meta_get_trend_chart`**: Gera gráficos ASCII para visualizar tendências de métricas (ex: Spend, ROAS) ao longo do tempo.

## 🛠️ Instalação e Configuração

### Pré-requisitos

*   Python 3.10+
*   Token de Acesso da API da Meta (Business Manager System User ou Token de Desenvolvedor)

### Passo a Passo

1.  **Clone o repositório:**
    ```bash
    git clone https://github.com/phwtsp/mcp-meta-ads.git
    cd mcp-meta-ads
    ```

2.  **Crie e ative um ambiente virtual:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # No Windows: venv\Scripts\activate
    ```

3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure as Variáveis de Ambiente:**
    Crie um arquivo `.env` na raiz do projeto (ou configure no seu ambiente) com o token de acesso:
    ```env
    META_ACCESS_TOKEN=seu_token_aqui_eaaxxx...
    ```

5.  **Configure os Clientes:**
    Crie um arquivo `clients.json` na raiz do projeto para mapear nomes amigáveis para IDs de conta de anúncios (`act_XXXXXXXX`):
    ```json
    {
        "Nome Do Cliente 1": "act_1234567890",
        "Nome Do Cliente 2": "act_0987654321"
    }
    ```

## 🔌 Uso com Clientes MCP

Para usar este servidor com clientes MCP (como Claude Desktop ou Cursor), adicione a configuração ao seu arquivo de configurações MCP.

Exemplo de configuração (`mcp.json` ou similar):

```json
{
  "mcpServers": {
    "meta-ads": {
      "command": "/caminho/para/projeto/venv/bin/python",
      "args": [
        "/caminho/para/projeto/server.py"
      ],
      "env": {
        "META_ACCESS_TOKEN": "seu_token_aqui"
      }
    }
  }
}
```

> **Nota:** Certifique-se de usar o caminho absoluto para o executável `python` dentro do ambiente virtual (`venv`) e para o script `server.py`.

## 📦 Estrutura do Projeto

*   `server.py`: Código fonte principal do servidor MCP.
*   `.env`: (Não versionado) Armazena credenciais sensíveis.
*   `clients.json`: (Não versionado) Arquivo de configuração de contas de clientes.
*   `requirements.txt`: Lista de dependências Python.

## 🛡️ Segurança

Este projeto lida com tokens de acesso sensíveis.
*   Nunca commite o arquivo `.env` ou `clients.json` com dados reais.
*   O arquivo `.gitignore` já está configurado para excluir estes arquivos.

## 📄 Licença

[Inserir Licença, ex: MIT]
