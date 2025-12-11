from mcp.server.fastmcp import FastMCP
import requests
import os
import json

# --- CONFIGURAÇÃO DE CLIENTES ---
# Pega o caminho absoluto da pasta onde este script (server.py) está
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENTS_FILE = os.path.join(BASE_DIR, 'clients.json')

try:
    with open(CLIENTS_FILE, 'r', encoding='utf-8') as f:
        CLIENTS = json.load(f)
except FileNotFoundError:
    # Se der erro, mostra onde ele tentou procurar (ajuda no debug)
    raise FileNotFoundError(f"Arquivo não encontrado no caminho: {CLIENTS_FILE}")

ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN") 
BASE_URL = "https://graph.facebook.com/v21.0"

mcp = FastMCP("Meta Ads Advanced")

def get_headers():
    return {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

def resolve_account_id(account_identifier: str) -> str:
    if account_identifier.startswith("act_"):
        return account_identifier
    for name, acc_id in CLIENTS.items():
        if name.lower() in account_identifier.lower():
            return acc_id
    return None

def format_currency(value):
    try:
        return f"{float(value):.2f}"
    except:
        return "0.00"

def parse_actions(actions_list):
    """
    Transforma a lista complexa de ações do Facebook em string legível.
    Ex: De [{'action_type': 'purchase', 'value': 5}] para 'purchase: 5'
    """
    if not actions_list:
        return "Nenhuma conversão"
    
    summary = []
    # Ações prioritárias para destacar (adicione as que importam para você)
    priority = ['purchase', 'lead', 'link_click', 'video_view', 'post_engagement']
    
    # Dicionário para acesso rápido
    acts = {item['action_type']: item['value'] for item in actions_list}
    
    # Retorna formatado
    results = []
    for k, v in acts.items():
        if k in priority or 'purchase' in k: # Pega purchase e variantes
            results.append(f"{k}: {v}")
            
    return " | ".join(results) if results else "Outras ações (sem prioridade)"

# --- FERRAMENTAS ---

@mcp.tool()
def list_available_clients() -> str:
    """Lista clientes configurados."""
    if not CLIENTS: return "Nenhum cliente."
    return "\n".join([f"- {name}: {aid}" for name, aid in CLIENTS.items()])

@mcp.tool()
def get_structure(account_identifier: str, campaign_id: str = None) -> str:
    """
    Navegação Hierárquica (Drill-down).
    1. Se der apenas a conta: Lista Campanhas.
    2. Se der o ID da campanha: Lista Conjuntos (AdSets) e Anúncios (Ads) dentro dela.
    Use isso para descobrir os IDs antes de pedir métricas.
    """
    acc_id = resolve_account_id(account_identifier)
    if not acc_id: return "Conta não encontrada."

    if not campaign_id:
        # Nível 1: Listar Campanhas
        url = f"{BASE_URL}/{acc_id}/campaigns"
        params = {"fields": "name,status,objective", "limit": 50}
        resp = requests.get(url, headers=get_headers(), params=params)
        data = resp.json().get("data", [])
        
        txt = f"Campanhas na conta {acc_id}:\n"
        for c in data:
            txt += f"ID: {c['id']} | [{c['status']}] {c['name']}\n"
        return txt
    else:
        # Nível 2: Listar AdSets e Ads dentro da Campanha
        # Pegamos adsets primeiro
        url_sets = f"{BASE_URL}/{campaign_id}/adsets"
        params_sets = {"fields": "name,status,billing_event"}
        resp_sets = requests.get(url_sets, headers=get_headers(), params=params_sets)
        adsets = resp_sets.json().get("data", [])
        
        # Pegamos ads
        url_ads = f"{BASE_URL}/{campaign_id}/ads"
        params_ads = {"fields": "name,status,adset_id"}
        resp_ads = requests.get(url_ads, headers=get_headers(), params=params_ads)
        ads = resp_ads.json().get("data", [])
        
        txt = f"Estrutura da Campanha {campaign_id}:\n\n--- CONJUNTOS DE ANÚNCIOS ---\n"
        for ads_item in adsets:
            txt += f"ID: {ads_item['id']} | {ads_item['name']} ({ads_item['status']})\n"
            
        txt += "\n--- ANÚNCIOS ---\n"
        for ad in ads:
            txt += f"ID: {ad['id']} | {ad['name']} (Set: {ad['adset_id']})\n"
            
        return txt

@mcp.tool()
def get_analytics(object_id: str, date_preset: str = "maximum", breakdown_by_time: bool = False) -> str:
    """
    A ferramenta principal de análise.
    Args:
        object_id: ID de Conta, Campanha, AdSet ou Ad.
        date_preset: 'today', 'yesterday', 'this_month', 'last_7d', 'last_30d', 'maximum'.
        breakdown_by_time: Se True, traz dados dia a dia.
    """
    url = f"{BASE_URL}/{object_id}/insights"
    
    # 1. LISTA DE CAMPOS CORRIGIDA (Sem 'roas' direto)
    fields = [
        "campaign_name", "adset_name", "ad_name", "balance",
        "spend", "impressions", "clicks", "cpc", "cpm", "ctr", "frequency",
        "actions",          # Contagem de conversões (compras, leads)
        "action_values",    # Valor monetário das conversões (para calcular ROAS)
        "cost_per_action_type" # CPA por tipo
    ]
    
    params = {
        "fields": ",".join(fields),
        "date_preset": date_preset,
        "limit": 100
    }
    
    if breakdown_by_time:
        params["time_increment"] = "1"
        
    response = requests.get(url, headers=get_headers(), params=params)
    
    if response.status_code != 200:
        return f"Erro API: {response.text}"
        
    data = response.json().get("data", [])
    if not data:
        return "Sem dados para este período/ID."

    output = f"Relatório Analítico para ID {object_id} ({date_preset}):\n"
    
    for row in data:
        date_ref = row.get('date_start', 'Total')
        prefix = f"📅 {date_ref}" if breakdown_by_time else "📊 Total"
            
        # Extração de dados básicos
        spend = float(row.get('spend', 0))
        ctr = row.get('ctr', '0')
        cpc = row.get('cpc', '0')
        
        # --- CÁLCULO MANUAL DO ROAS ---
        purchase_value = 0.0
        # action_values vem como lista: [{'action_type': 'purchase', 'value': '150.00'}, ...]
        vals = row.get('action_values', [])
        if vals:
            for item in vals:
                # Somamos o valor se for compra (purchase) ou omni_purchase
                if item.get('action_type') == 'purchase':
                    purchase_value += float(item.get('value', 0))
        
        # Evitar divisão por zero
        roas = (purchase_value / spend) if spend > 0 else 0.0
        
        # Formatação das ações (conversões)
        actions_str = parse_actions(row.get('actions', []))
        
        # Identificação do nome (hierarquia)
        name_ref = row.get('ad_name') or row.get('adset_name') or row.get('campaign_name') or "Geral"
        
        output += (
            f"{prefix} | {name_ref}\n"
            f"  💰 Gasto: R$ {spend:.2f} | Retorno (Value): R$ {purchase_value:.2f}\n"
            f"  📈 ROAS: {roas:.2f}x\n"
            f"  🖱️ CPC: R$ {cpc} | CTR: {ctr}%\n"
            f"  🎯 Conversões: {actions_str}\n"
            f"  ------------------------------------------------\n"
        )
        
    return output

@mcp.tool()
def get_ad_creative_details(ad_id: str) -> str:
    """
    Analisa o CRIATIVO de um anúncio específico.
    Traz Imagem, Título, Texto e Link.
    """
    # Passo 1: Pegar o ID do Creative a partir do ID do Ad
    url_ad = f"{BASE_URL}/{ad_id}"
    params_ad = {"fields": "creative"}
    resp_ad = requests.get(url_ad, headers=get_headers(), params=params_ad)
    creative_id = resp_ad.json().get("creative", {}).get("id")
    
    if not creative_id:
        return "Não foi possível encontrar o criativo deste anúncio."
        
    # Passo 2: Pegar os detalhes do Creative
    url_cre = f"{BASE_URL}/{creative_id}"
    # Campos comuns de criativos (imagem, corpo, titulo, call to action)
    fields = "name,title,body,image_url,thumbnail_url,call_to_action_type,object_story_spec"
    
    resp_cre = requests.get(url_cre, headers=get_headers(), params={"fields": fields})
    data = resp_cre.json()
    
    # Tratamento para posts existentes (Dark posts) vs Ads criados direto
    title = data.get('title') or "N/A (Post Existente?)"
    body = data.get('body') or "N/A"
    img = data.get('image_url') or data.get('thumbnail_url') or "N/A"
    
    # Tenta extrair dados se for um post vinculado (object_story_spec)
    if 'object_story_spec' in data:
        link_data = data['object_story_spec'].get('link_data', {})
        if not title or title == "N/A": title = link_data.get('name')
        if not body or body == "N/A": body = link_data.get('message')
        if not img or img == "N/A": img = link_data.get('picture')

    return (
        f"🎨 Detalhes do Criativo (ID: {creative_id}):\n"
        f"📌 Título: {title}\n"
        f"📝 Texto (Body): {body}\n"
        f"🖼️ Imagem/Thumb: {img}\n"
        f"👉 CTA: {data.get('call_to_action_type', 'N/A')}\n"
    )

@mcp.tool()
def get_account_balance(account_identifier: str) -> str:
    """
    Obtém o saldo (balance), limite de gastos e total gasto da conta.
    Útil para saber se a conta está com saldo devedor ou pré-pago acabando.
    """
    # 1. Resolve o ID usando a função simples do seu código
    acc_id = resolve_account_id(account_identifier)
    if not acc_id:
        return f"Cliente '{account_identifier}' não encontrado."

    # 2. Busca dados diretos da conta (Endpoint da conta, não insights)
    url = f"{BASE_URL}/{acc_id}"
    
    params = {
        "fields": "name,balance,currency,amount_spent,spend_cap,account_status,min_daily_budget"
    }
    
    # 3. Usa o requests direto com seus headers globais
    response = requests.get(url, headers=get_headers(), params=params)
    
    if response.status_code != 200:
        return f"Erro ao buscar saldo: {response.text}"
        
    data = response.json()
    
    # --- Lógica de Formatação (Mantida igual) ---
    currency = data.get("currency", "BRL")
    
    # O Facebook retorna em centavos, dividimos por 100
    raw_balance = int(data.get("balance", 0))
    balance_real = raw_balance / 100.0
    
    raw_spent = int(data.get("amount_spent", 0))
    spent_real = raw_spent / 100.0
    
    # Mapeamento de Status
    status_map = {
        1: "🟢 Ativa", 
        2: "🔴 Desativada", 
        3: "🟠 Não Liquidada (Pagamento Pendente)", 
        7: "⏳ Pendente de Revisão", 
        8: "⏳ Pendente de Liquidação", 
        9: "📅 Em Período de Graça"
    }
    status_code = data.get("account_status")
    status_txt = status_map.get(status_code, f"Status código {status_code}")

    output = (
        f"💳 Financeiro da Conta: {data.get('name')} ({acc_id})\n"
        f"Status: {status_txt}\n"
        f"-----------------------------------\n"
        f"💰 Balance (A Pagar/Crédito): {currency} {balance_real:,.2f}\n"
        f"📉 Total Gasto (Vitalício): {currency} {spent_real:,.2f}\n"
    )
    
    # Verifica Spend Cap (Limite da Conta)
    if "spend_cap" in data and data["spend_cap"]:
        cap_real = int(data["spend_cap"]) / 100.0
        remaining = cap_real - spent_real
        output += f"🚧 Limite da Conta (Cap): {currency} {cap_real:,.2f}\n"
        output += f"⚠️ Restante antes de travar: {currency} {remaining:,.2f}\n"
        
    return output

if __name__ == "__main__":
    mcp.run()