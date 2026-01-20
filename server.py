from mcp.server.fastmcp import FastMCP
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import json
from datetime import datetime, timedelta


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
except json.JSONDecodeError:
    print(f"Erro: O arquivo {CLIENTS_FILE} não é um JSON válido. Iniciando com lista vazia.")
    CLIENTS = {}

ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN") 
BASE_URL = "https://graph.facebook.com/v21.0"
TIMEOUT = 30  # Timeout padrão para requisições em segundos

mcp = FastMCP("Meta Ads Advanced")

# Otimização: Sessão global para reutilizar conexões TCP (Connection Pooling)
session = requests.Session()
session.headers.update({
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
})



def fetch_all_pages(url: str, params: dict = None) -> list:
    """
    Helper para buscar todas as páginas de resultados (paginação automática).
    """
    all_data = []
    current_url = url
    current_params = params
    
    while current_url:
        try:
            resp = session.get(current_url, params=current_params, timeout=TIMEOUT)
            if resp.status_code != 200:
                # Se houver erro, retornamos o que já coletamos
                break
                
            data_json = resp.json()
            items = data_json.get("data", [])
            if not items:
                break
                
            all_data.extend(items)
            
            # Próxima página
            current_url = data_json.get("paging", {}).get("next")
            current_params = None # O link 'next' já tem os parâmetros codificados
            
        except Exception:
            break
            
    return all_data

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

def parse_fb_date(date_str: str) -> tuple[str, datetime]:
    """
    Normaliza datas do Facebook para texto formatado e objeto datetime.
    Aceita "YYYY-MM-DD" ou ISO 8601 "YYYY-MM-DDTHH:MM..."
    Retorna: (str_formatada_BR, objeto_datetime)
    """
    if not date_str:
        return "", None
    try:
        dt = datetime.fromisoformat(date_str) if 'T' in date_str else datetime.strptime(date_str[:10], "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y"), dt
    except ValueError:
        return date_str[:10], None

def calculate_metrics(data_row: dict) -> dict:
    """
    Calcula métricas derivadas (ROAS, CPA) a partir de uma linha de dados da API.
    Retorna dicionário com os valores calculados.
    """
    spend = float(data_row.get('spend', 0))
    
    # Receita (Purchase Value)
    purchase_value = 0.0
    vals = data_row.get('action_values', [])
    if vals:
        for item in vals:
            if item.get('action_type') == 'purchase':
                purchase_value += float(item.get('value', 0))
    
    # Compras (Purchase Count)
    purchase_count = 0
    acts = data_row.get('actions', [])
    if acts:
        for item in acts:
            if item.get('action_type') == 'purchase':
                purchase_count += float(item.get('value', 0))

    roas = (purchase_value / spend) if spend > 0 else 0.0
    cpa = (spend / purchase_count) if purchase_count > 0 else 0.0

    return {
        "spend": spend,
        "purchase_value": purchase_value,
        "purchase_count": purchase_count,
        "roas": roas,
        "cpa": cpa
    }

# --- FERRAMENTAS ---

@mcp.tool()
def meta_list_clients() -> str:
    """Lista clientes configurados."""
    if not CLIENTS: return "Nenhum cliente."
    return "\n".join([f"- {name}: {aid}" for name, aid in CLIENTS.items()])

@mcp.tool()
def meta_get_structure(account_identifier: str, campaign_id: str = None) -> str:
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
        # Adicionados campos de orçamento e datas
        params = {
            "fields": "name,status,objective,daily_budget,lifetime_budget,spend_cap,buying_type,start_time,stop_time",
            "limit": 50
        }

        
        # Paginação automática
        data = fetch_all_pages(url, params)
        
        txt = f"Campanhas na conta {acc_id}:\n"
        for c in data:
            # Tratamento de orçamento
            b_parts = []
            if c.get("daily_budget"): b_parts.append(f"Diário: R${int(c['daily_budget'])/100:.2f}")
            if c.get("lifetime_budget"): b_parts.append(f"Total: R${int(c['lifetime_budget'])/100:.2f}")
            if c.get("spend_cap"): b_parts.append(f"Cap: R${int(c['spend_cap'])/100:.2f}")
            
            budget_info = " | ".join(b_parts) if b_parts else "N/A (Verificar CBO ou Sem Limite)"
            
            # Parse e Formatação de Datas (Programação)
            start_fmt, s_dt = parse_fb_date(c.get("start_time", ""))
            stop_fmt, e_dt = parse_fb_date(c.get("stop_time", ""))
            
            schedule_txt = "N/A"
            if start_fmt:
                if stop_fmt:
                    days = (e_dt - s_dt).days if (s_dt and e_dt) else "?"
                    schedule_txt = f"{start_fmt} - {stop_fmt} ({days} dias)"
                else:
                    schedule_txt = f"{start_fmt} - Contínuo"
            
            txt += (f"ID: {c['id']} | [{c['status']}] {c['name']}\n"
                    f"   💰 {budget_info} | � Programação: {schedule_txt} | 🎯 {c['objective']}\n"
                    f"   ------------------------------------------------\n")
        return txt
    else:
        # Nível 2: Listar AdSets e Ads dentro da Campanha
        # Otimização: Paralelismo para buscar AdSets e Ads simultaneamente
        
        def fetch_adsets():
            url_sets = f"{BASE_URL}/{campaign_id}/adsets"
            params_sets = {
                "fields": "name,status,billing_event,daily_budget,lifetime_budget,start_time,end_time,adset_schedule"
            }
            return fetch_all_pages(url_sets, params_sets)

        def fetch_ads():
            url_ads = f"{BASE_URL}/{campaign_id}/ads"
            params_ads = {"fields": "name,status,adset_id"}
            return fetch_all_pages(url_ads, params_ads)

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_sets = executor.submit(fetch_adsets)
            future_ads = executor.submit(fetch_ads)
            adsets = future_sets.result()
            ads = future_ads.result()
        
        txt = f"Estrutura da Campanha {campaign_id}:\n\n--- CONJUNTOS DE ANÚNCIOS (ADSETS) ---\n"
        for ads_item in adsets:
            # Orçamento
            b_parts = []
            if ads_item.get("daily_budget"): b_parts.append(f"Diário: R${int(ads_item['daily_budget'])/100:.2f}")
            if ads_item.get("lifetime_budget"): b_parts.append(f"Total: R${int(ads_item['lifetime_budget'])/100:.2f}")
            
            budget_info = " | ".join(b_parts) if b_parts else "Definido na Campanha (CBO) ou N/A"
                
            # Parse e Formatação de Datas (Programação)
            start_fmt, s_dt = parse_fb_date(ads_item.get("start_time", ""))
            end_fmt, e_dt = parse_fb_date(ads_item.get("end_time", ""))
            
            schedule_txt = "N/A"
            if start_fmt:
                if end_fmt:
                    days = (e_dt - s_dt).days if (s_dt and e_dt) else "?"
                    schedule_txt = f"{start_fmt} - {end_fmt} ({days} dias)"
                else:
                    schedule_txt = f"{start_fmt} - Contínuo"
            
            txt += (f"ID: {ads_item['id']} | {ads_item['name']} ({ads_item['status']})\n"
                    f"   💰 {budget_info} | � Programação: {schedule_txt}\n")
            
        txt += "\n--- ANÚNCIOS (ADS) ---\n"
        for ad in ads:
            txt += f"ID: {ad['id']} | {ad['name']} (Status: {ad['status']})\n"
            
        return txt

@mcp.tool()
def meta_get_analytics(
    object_id: str, 
    date_preset: str = "maximum", 
    days_ago: int = None, 
    level: str = None, 
    breakdown_by_time: bool = False
) -> str:
    """
    A ferramenta principal de análise.
    Args:
        object_id: ID de Conta, Campanha, AdSet ou Ad.
        date_preset: 'today', 'yesterday', 'this_month', 'last_7d', 'last_30d', 'maximum'.
        days_ago: Se informado, ignora date_preset e pega os últimos X dias (ex: 15).
        level: Nível de agregação ('campaign', 'adset', 'ad'). Se vazio, agrega pelo objeto.
        breakdown_by_time: Se True, traz dados dia a dia.
    """
    url = f"{BASE_URL}/{object_id}/insights"
    
    # 1. LISTA DE CAMPOS ATUALIZADA
    fields = [
        "campaign_name", "adset_name", "ad_name", "ad_id",
        "spend", "impressions", "clicks", "cpc", "cpm", "ctr", "frequency", "reach",
        "actions",          # Resultados brutos
        "action_values",    # Valor monetário
        "cost_per_action_type" # Custo por resultado
    ]
    
    params = {
        "fields": ",".join(fields),
        "limit": 100
    }

    if level:
        params["level"] = level

    if days_ago:
        today = datetime.now()
        start_date = today - timedelta(days=days_ago) # Pega X dias atrás
        
        # Define intervalo customizado (inclusive dia atual)
        since_str = start_date.strftime("%Y-%m-%d")
        until_str = today.strftime("%Y-%m-%d")
        
        params["time_range"] = json.dumps({"since": since_str, "until": until_str})
    else:
        params["date_preset"] = date_preset
    
    if breakdown_by_time:
        params["time_increment"] = "1"
        
    # Paginação automática
    data = fetch_all_pages(url, params)

    if not data:
        return "Sem dados para este período/ID."

    # --- NOVO: BUSCA DE IMAGENS (Se for nível 'ad') ---
    ad_images = {}
    if level == 'ad':
        # Coleta IDs únicos de ads
        ad_ids = list(set([row.get('ad_id') for row in data if row.get('ad_id')]))
        
        # Função auxiliar para buscar lote
        def fetch_img_batch(chunk_ids):
            ids_str = ",".join(chunk_ids)
            url_imgs = f"{BASE_URL}/"
            params_imgs = {
                "ids": ids_str,
                "fields": "creative{thumbnail_url,image_url}"
            }
            try:
                r = session.get(url_imgs, params=params_imgs, timeout=TIMEOUT)
                return r.json() if r.status_code == 200 else {}
            except:
                return {}

        # Otimização: Busca paralela de lotes de imagens
        chunk_size = 50
        chunks = [ad_ids[i:i + chunk_size] for i in range(0, len(ad_ids), chunk_size)]
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_chunk = {executor.submit(fetch_img_batch, chunk): chunk for chunk in chunks}
            for future in as_completed(future_to_chunk):
                imgs_data = future.result()
                if imgs_data:
                    for aid, ainfo in imgs_data.items():
                        cre = ainfo.get('creative', {})
                        img_link = cre.get('thumbnail_url') or cre.get('image_url') or "Sem imagem"
                        ad_images[aid] = img_link

    output = f"Relatório Analítico para ID {object_id} ({date_preset}):\n"
    
    for row in data:
        date_ref = row.get('date_start', 'Total')
        prefix = f"📅 {date_ref}" if breakdown_by_time else "📊 Total"
            
        # Extração de dados básicos
        # Data e Métricas
        metrics = calculate_metrics(row)
        spend = metrics["spend"]
        roas = metrics["roas"]
        purchase_value = metrics["purchase_value"]
        
        ctr = row.get('ctr', '0')
        cpc = row.get('cpc', '0')
        cpm = row.get('cpm', '0')
        reach = row.get('reach', '0')
        freq = row.get('frequency', '0')
        impressions = row.get('impressions', '0')
        clicks = row.get('clicks', '0')
        
        # Formatação das ações
        actions_str = parse_actions(row.get('actions', []))
        
        # CPA (Cost Per Result) - Simplificado para principais
        cpa_str = parse_actions(row.get('cost_per_action_type', []))
        
        # Identificação do nome
        name_ref = row.get('ad_name') or row.get('adset_name') or row.get('campaign_name') or "Geral"
        
        # Inserção da Imagem (se houver)
        img_line = ""
        if level == 'ad':
            aid = row.get('ad_id')
            img_url = ad_images.get(aid)
            if img_url:
                img_line = f"  🖼️ Imagem: {img_url}\n"
        
        output += (
            f"{prefix} | {name_ref}\n"
            f"  💰 Gasto: R$ {spend:.2f} | ROAS: {roas:.2f}x | Receita: R$ {purchase_value:.2f}\n"
            f"  👁️ Impressões: {impressions} | Alcance: {reach} | Freq: {freq}\n"
            f"  🖱️ Cliques: {clicks} | CPC: R$ {cpc} | CPM: R$ {cpm} | CTR: {ctr}%\n"
            f"{img_line}"
            f"  🎯 Resultados: {actions_str}\n"
            f"  💸 Custo p/ Resultado: {cpa_str}\n"
            f"  ------------------------------------------------\n"
        )
        
    return output

@mcp.tool()
def meta_get_ad_creative_details(ad_id: str) -> str:
    """
    Analisa o CRIATIVO de um anúncio específico.
    Traz Imagem, Título, Texto e Link.
    """
    # Passo 1: Pegar o ID do Creative a partir do ID do Ad
    url_ad = f"{BASE_URL}/{ad_id}"
    params_ad = {"fields": "creative"}
    resp_ad = session.get(url_ad, params=params_ad, timeout=TIMEOUT)
    creative_id = resp_ad.json().get("creative", {}).get("id")
    
    if not creative_id:
        return "Não foi possível encontrar o criativo deste anúncio."
        
    # Passo 2: Pegar os detalhes do Creative
    url_cre = f"{BASE_URL}/{creative_id}"
    # Campos comuns de criativos (imagem, corpo, titulo, call to action)
    fields = "name,title,body,image_url,thumbnail_url,call_to_action_type,object_story_spec"
    
    resp_cre = session.get(url_cre, params={"fields": fields}, timeout=TIMEOUT)
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
def meta_get_account_balance(account_identifier: str) -> str:
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
    response = session.get(url, params=params, timeout=TIMEOUT)
    
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

@mcp.tool()
def meta_get_demographics(object_id: str, date_preset: str = "maximum") -> str:
    """
    Analisa o perfil do público (Idade, Gênero) e Plataforma/Posicionamento.
    Use para descobrir: "Qual idade compra mais?" ou "Instagram vs Facebook".
    """
    # 1. Breakdown demográfico (Idade + Gênero)
    url = f"{BASE_URL}/{object_id}/insights"
    params_demo = {
        "fields": "spend,actions,action_values",
        "breakdowns": "age,gender",
        "date_preset": date_preset,
        "limit": 100
    }
    
    # 2. Breakdown de Plataforma
    params_plat = {
        "fields": "spend,actions,action_values",
        "breakdowns": "publisher_platform", # facebook, instagram, audience_network
        "date_preset": date_preset,
        "limit": 100
    }
    
    # Execução em parelelo
    with ThreadPoolExecutor(max_workers=2) as executor:
        f_demo = executor.submit(session.get, url, params=params_demo, timeout=TIMEOUT)
        f_plat = executor.submit(session.get, url, params=params_plat, timeout=TIMEOUT)
        
        data_demo = f_demo.result().json().get("data", [])
        data_plat = f_plat.result().json().get("data", [])

    # Processador de métricas simples
    def process_rows(rows, key_generators):
        results = []
        for r in rows:
            label = " | ".join([r.get(k, "N/A") for k in key_generators])
            
            metrics = calculate_metrics(r)
            spend = metrics["spend"]
            roas = metrics["roas"]
            cpa = metrics["cpa"]
            purch_count = metrics["purchase_count"]
            
            results.append((label, spend, roas, cpa, purch_count))
        
        # Ordena por Spend (Gasto) decrescente
        return sorted(results, key=lambda x: x[1], reverse=True)

    rows_demo = process_rows(data_demo, ["age", "gender"])
    rows_plat = process_rows(data_plat, ["publisher_platform"])
    
    # Formatação de saída
    out = f"👥 Análise Demográfica & Plataforma (ID: {object_id})\n\n"
    
    out += "🆔 IDADE e GÊNERO (Top 10 por Gasto):\n"
    out += f"{'Segmento':<20} | {'Gasto':<10} | {'ROAS':<6} | {'CPA':<8} | {'Compras'}\n"
    out += "-" * 75 + "\n"
    for item in rows_demo[:10]: # Top 10
        out += f"{item[0]:<20} | R${item[1]:<8.0f} | {item[2]:<5.2f}x | R${item[3]:<6.0f} | {int(item[4])}\n"
        
    out += "\n📱 PLATAFORMAS:\n"
    out += f"{'Plataforma':<20} | {'Gasto':<10} | {'ROAS':<6} | {'CPA':<8} | {'Compras'}\n"
    out += "-" * 75 + "\n"
    for item in rows_plat:
        out += f"{item[0]:<20} | R${item[1]:<8.0f} | {item[2]:<5.2f}x | R${item[3]:<6.0f} | {int(item[4])}\n"
        
    return out

@mcp.tool()
def meta_compare_performance(ids_str: str, date_preset: str = "maximum") -> str:
    """
    Compara métricas de múltiplos IDs lado a lado.
    Args:
        ids_str: IDs separados por vírgula (ex: "123,456,789").
    """
    id_list = [x.strip() for x in ids_str.split(",") if x.strip()]
    
    def fetch_one(oid):
        # Reutiliza get_analytics mas forçando level=None p/ pegar só o total
        # Mas get_analytics retorna texto. Vamos chamar API direta p/ ter dados brutos.
        url = f"{BASE_URL}/{oid}/insights"
        fields = "campaign_name,adset_name,ad_name,spend,cpc,ctr,actions,action_values"
        p = {"fields": fields, "date_preset": date_preset, "limit": 1}
        return session.get(url, params=p, timeout=TIMEOUT).json()

    # Fetch paralelo
    results = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_one, i): i for i in id_list}
        for f in as_completed(futures):
            oid = futures[f]
            try:
                data = f.result().get("data", [{}])[0]
                results[oid] = data
            except:
                results[oid] = {}

    # Monta Tabela Comparativa via Texto Formatado
    # Cabeçalho
    header = f"{'Nome/ID':<30} | {'Gasto':<12} | {'ROAS':<6} | {'CTR':<6} | {'CPA (Compra)'}"
    out = "⚖️ Comparativo de Performance\n"
    out += header + "\n" + "-" * len(header) + "\n"
    
    for oid in id_list:
        d = results.get(oid, {})
        if not d:
            out += f"{oid:<30} | (Sem dados)\n"
            continue
            
        name = d.get('ad_name') or d.get('adset_name') or d.get('campaign_name') or oid
        name = d.get('ad_name') or d.get('adset_name') or d.get('campaign_name') or oid
        ctr = float(d.get('ctr', 0))
        
        metrics = calculate_metrics(d)
        spend = metrics["spend"]
        roas = metrics["roas"]
        cpa = metrics["cpa"]
        
        # Truncar nome se for longo
        d_name = (name[:27] + "...") if len(name) > 30 else name
        
        out += f"{d_name:<30} | R${spend:<10.2f} | {roas:<5.2f}x | {ctr:<5.2f}% | R${cpa:<5.2f}\n"

    return out

@mcp.tool()
def meta_get_trend_chart(object_id: str, metric: str = "spend", days: int = 15) -> str:
    """
    Gera um gráfico ASCII temporal de uma métrica específica.
    Métricas suportadas: 'spend', 'roas', 'cpa', 'ctr', 'cpc', 'clicks', 'impressions'.
    Args:
        metric: A métrica a visualizar.
        days: Quantos dias passados visualizar.
    """
    today = datetime.now()
    since = (today - timedelta(days=days)).strftime("%Y-%m-%d")
    until = today.strftime("%Y-%m-%d")
    
    url = f"{BASE_URL}/{object_id}/insights"
    fields = "spend,actions,action_values,cpc,ctr,clicks,impressions"
    params = {
        "fields": fields,
        "time_increment": "1",
        "time_range": json.dumps({"since": since, "until": until}),
        "limit": 100
    }
    
    resp = session.get(url, params=params, timeout=TIMEOUT)
    data = resp.json().get("data", [])
    
    if not data: return "Sem dados para gerar gráfico."
    
    # Extrair valores
    chart_data = [] # (date_str, value)
    
    for row in data:
        dt_str = row.get("date_start", "")[5:] # pega mm-dd
        val = 0.0
        
        # Lógica de extração baseada na métrica
        mets = calculate_metrics(row)
        
        if metric == "spend":
            val = mets["spend"]
        elif metric == "roas":
            val = mets["roas"]
        elif metric == "cpa":
            val = mets["cpa"]
        elif metric in ["ctr", "cpc", "clicks", "impressions"]:
            # Estes campos vêm diretos da API
            try:
                val = float(row.get(metric, 0))
            except: 
                val = 0.0
                
        chart_data.append((dt_str, val))
        
    # Gerador de ASCII Chart
    # Normalizar para largura fixa (ex: 30 chars de barra)
    if not chart_data: return "Dados vazios."
    
    values = [x[1] for x in chart_data]
    max_val = max(values) if values else 1
    if max_val == 0: max_val = 1
    
    bar_width = 30
    
    out = f"📈 Gráfico de {metric.upper()} (Últimos {days} dias)\n"
    out += f"Mín: {min(values):.2f} | Máx: {max_val:.2f}\n\n"
    
    for dt, v in chart_data:
        # Tamanho da barra proporcional
        filled = int((v / max_val) * bar_width)
        bar = "█" * filled
        # Espaçamento
        out += f"{dt} | {bar:<{bar_width}} {v:.2f}\n"
        
    return out

if __name__ == "__main__":
    mcp.run()