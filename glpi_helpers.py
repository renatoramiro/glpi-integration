"""
Funções auxiliares para interação com a API do GLPI.

Este módulo contém todas as funções de baixo nível para comunicação
com o GLPI, incluindo gerenciamento de sessões, operações CRUD em tickets,
e formatação de dados.
"""

import os
import logging
import requests
from typing import Optional, List, Dict, Any

# Configuração de logging
logger = logging.getLogger(__name__)

# Configurações do GLPI (carregadas das variáveis de ambiente)
GLPI_BASE_URL = os.getenv("GLPI_BASE_URL", "http://localhost:8080/apirest.php")
GLPI_USER_TOKEN = os.getenv("USER_TOKEN", "")
GLPI_APP_TOKEN = os.getenv("APP_TOKEN", "")


# ============================================================================
# GERENCIAMENTO DE SESSÃO
# ============================================================================

def init_glpi_session() -> Optional[str]:
    """
    Inicializa uma sessão com o GLPI.
    
    Returns:
        Token da sessão se bem-sucedido, None caso contrário
    """
    url = f"{GLPI_BASE_URL}/initSession"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'user_token {GLPI_USER_TOKEN}',
        'App-Token': GLPI_APP_TOKEN
    }
    
    try:
        response = requests.get(url, headers=headers, verify=False)
        if response.status_code == 200:
            return response.json()['session_token']
        else:
            logger.error(f"Falha ao iniciar sessão GLPI: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Erro ao iniciar sessão GLPI: {str(e)}")
        return None


def kill_glpi_session(session_token: str) -> bool:
    """
    Finaliza a sessão com o GLPI.
    
    Args:
        session_token: Token da sessão a ser finalizada
        
    Returns:
        True se a sessão foi finalizada com sucesso, False caso contrário
    """
    url = f"{GLPI_BASE_URL}/killSession"
    headers = {
        'Content-Type': 'application/json',
        'Session-Token': session_token,
        'App-Token': GLPI_APP_TOKEN
    }
    
    try:
        response = requests.get(url, headers=headers, verify=False)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Erro ao finalizar sessão GLPI: {str(e)}")
        return False


# ============================================================================
# OPERAÇÕES COM TICKETS
# ============================================================================

def get_ticket_details(ticket_id: int, session_token: str) -> Optional[Dict[str, Any]]:
    """
    Obtém os detalhes de um ticket específico.
    
    Args:
        ticket_id: ID do ticket no GLPI
        session_token: Token da sessão
        
    Returns:
        Dicionário com os detalhes do ticket ou None em caso de erro
    """
    url = f"{GLPI_BASE_URL}/Ticket/{ticket_id}"
    headers = {
        'Content-Type': 'application/json',
        'Session-Token': session_token,
        'App-Token': GLPI_APP_TOKEN
    }
    
    try:
        response = requests.get(url, headers=headers, verify=False)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Falha ao obter detalhes do ticket {ticket_id}: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Erro ao obter detalhes do ticket {ticket_id}: {str(e)}")
        return None


def create_ticket_in_glpi(
    title: str,
    external_id: str,
    session_token: str,
    entity_id: int = 0,
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> Optional[Dict[str, Any]]:
    """
    Cria um novo ticket no GLPI.
    
    Args:
        title: Título do ticket
        external_id: ID externo para referência cruzada
        session_token: Token da sessão GLPI
        entity_id: ID da entidade (default: 0 para entidade raiz)
        conversation_history: Lista com histórico da conversa (opcional)
            Formato: [{"speaker": "Cliente", "message": "texto"}, ...]
    
    Returns:
        Dicionário com informações do ticket criado ou None em caso de erro
    """
    url = f"{GLPI_BASE_URL}/Ticket"
    headers = {
        'Content-Type': 'application/json',
        'Session-Token': session_token,
        'App-Token': GLPI_APP_TOKEN
    }
    
    # Se houver histórico de conversa, formata como HTML
    final_content = ''
    if conversation_history:
        history_html = "<br><br><strong>Histórico de Conversa:</strong><br><ul>"
        for entry in conversation_history:
            if isinstance(entry, dict) and 'speaker' in entry and 'message' in entry:
                history_html += f"<li><strong>{entry['speaker']}:</strong> {entry['message']}</li>"
            else:
                history_html += f"<li>{entry}</li>"
        history_html += "</ul>"
        final_content += history_html
    
    ticket_data = {
        'name': title,
        'content': final_content,
        'entities_id': entity_id,
        'externalid': external_id
    }
    
    payload = {'input': ticket_data}
    
    try:
        response = requests.post(url, headers=headers, json=payload, verify=False)
        if response.status_code in [200, 201]:
            result = response.json()
            logger.info(f"Ticket criado com sucesso! ID: {result.get('id')}")
            return result
        else:
            logger.error(f"Falha ao criar ticket: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Erro ao criar ticket: {str(e)}")
        return None


def search_ticket_by_id(ticket_id: int, session_token: str) -> Optional[Dict[str, Any]]:
    """
    Busca um ticket pelo ID.
    
    Args:
        ticket_id: ID do ticket no GLPI
        session_token: Token da sessão
    
    Returns:
        Dados do ticket se encontrado, None caso contrário
    """
    try:
        ticket_details = get_ticket_details(ticket_id, session_token)
        if ticket_details:
            return ticket_details
        else:
            logger.warning(f"Ticket {ticket_id} não encontrado")
            return None
    except Exception as e:
        logger.error(f"Erro ao buscar ticket {ticket_id}: {str(e)}")
        return None


def search_ticket_by_external_id(external_id: str, session_token: str) -> Optional[int]:
    """
    Busca um ticket pelo ID externo.
    
    Args:
        external_id: ID externo do ticket
        session_token: Token da sessão
    
    Returns:
        ID do ticket se encontrado, None caso contrário
    """
    url = f"{GLPI_BASE_URL}/Ticket"
    headers = {
        'Content-Type': 'application/json',
        'Session-Token': session_token,
        'App-Token': GLPI_APP_TOKEN
    }
    
    # Busca os últimos 100 tickets
    params = {
        'range': '0-99',
        'order': 'DESC',
        'sort': 'id'
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, verify=False)
        if response.status_code == 200:
            tickets = response.json()
            logger.info(f"Buscando entre {len(tickets)} tickets...")
            
            # Filtra pelo externalid
            for ticket in tickets:
                ticket_externalid = ticket.get('externalid') or ticket.get('external_id')
                logger.debug(f"Ticket {ticket['id']}: externalid = {ticket_externalid}")
                
                if ticket_externalid == external_id:
                    logger.info(f"Ticket encontrado: ID {ticket['id']} com external_id {external_id}")
                    return ticket['id']
            
            logger.warning(f"Nenhum ticket encontrado com external_id: {external_id}")
            logger.info(f"Dica: Verifique se o ticket foi criado com o campo 'externalid' correto")
            return None
        else:
            logger.error(f"Falha ao buscar tickets: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Erro ao buscar ticket por external_id: {str(e)}")
        return None


# ============================================================================
# OPERAÇÕES COM FOLLOWUPS
# ============================================================================

def get_ticket_followups(ticket_id: int, session_token: str) -> List[Dict[str, Any]]:
    """
    Obtém os followups (observações) de um ticket específico.
    
    Args:
        ticket_id: ID do ticket no GLPI
        session_token: Token da sessão
        
    Returns:
        Lista de followups ou lista vazia em caso de erro
    """
    url = f"{GLPI_BASE_URL}/Ticket/{ticket_id}/ITILFollowup"
    headers = {
        'Content-Type': 'application/json',
        'Session-Token': session_token,
        'App-Token': GLPI_APP_TOKEN
    }
    
    try:
        response = requests.get(url, headers=headers, verify=False)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Falha ao obter followups do ticket {ticket_id}: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        logger.error(f"Erro ao obter followups do ticket {ticket_id}: {str(e)}")
        return []


def add_followup_to_ticket(
    ticket_id: int,
    content: str,
    session_token: str,
    is_private: int = 0
) -> Optional[Dict[str, Any]]:
    """
    Adiciona um followup (observação/mensagem) a um ticket.
    
    Args:
        ticket_id: ID do ticket no GLPI
        content: Conteúdo da mensagem
        session_token: Token da sessão
        is_private: 0 = público, 1 = privado
    
    Returns:
        Dicionário com informações do followup criado ou None em caso de erro
    """
    url = f"{GLPI_BASE_URL}/Ticket/{ticket_id}/ITILFollowup"
    headers = {
        'Content-Type': 'application/json',
        'Session-Token': session_token,
        'App-Token': GLPI_APP_TOKEN
    }
    
    followup_data = {
        "itemtype": "Ticket",
        "items_id": ticket_id,
        'content': content,
        'is_private': is_private
    }
    
    payload = {'input': followup_data}
    
    try:
        response = requests.post(url, headers=headers, json=payload, verify=False)
        if response.status_code in [200, 201]:
            return response.json()
        else:
            logger.error(f"Falha ao adicionar followup ao ticket {ticket_id}: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Erro ao adicionar followup ao ticket {ticket_id}: {str(e)}")
        return None


# ============================================================================
# OPERAÇÕES COM SOLUÇÕES
# ============================================================================

def get_ticket_solution(ticket_id: int, session_token: str) -> List[Dict[str, Any]]:
    """
    Obtém a solução de um ticket específico.
    
    Args:
        ticket_id: ID do ticket no GLPI
        session_token: Token da sessão
        
    Returns:
        Lista de soluções ou lista vazia em caso de erro
    """
    url = f"{GLPI_BASE_URL}/Ticket/{ticket_id}/ITILSolution"
    headers = {
        'Content-Type': 'application/json',
        'Session-Token': session_token,
        'App-Token': GLPI_APP_TOKEN
    }
    
    try:
        response = requests.get(url, headers=headers, verify=False)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Falha ao obter solução do ticket {ticket_id}: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        logger.error(f"Erro ao obter solução do ticket {ticket_id}: {str(e)}")
        return []


# ============================================================================
# OPERAÇÕES COM HISTÓRICO DE TICKETS
# ============================================================================

def get_ticket_logs(ticket_id: int, session_token: str) -> List[Dict[str, Any]]:
    """
    Obtém os logs de auditoria de um ticket específico.
    
    Args:
        ticket_id: ID do ticket no GLPI
        session_token: Token da sessão
        
    Returns:
        Lista de logs ou lista vazia em caso de erro
    """
    url = f"{GLPI_BASE_URL}/Ticket/{ticket_id}/Log"
    headers = {
        'Content-Type': 'application/json',
        'Session-Token': session_token,
        'App-Token': GLPI_APP_TOKEN
    }
    
    try:
        response = requests.get(url, headers=headers, verify=False)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Falha ao obter logs do ticket {ticket_id}: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        logger.error(f"Erro ao obter logs do ticket {ticket_id}: {str(e)}")
        return []


def search_all_tickets(
    session_token: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status_filter: Optional[int] = None,
    entity_id: Optional[int] = None,
    range_start: int = 0,
    range_end: int = 1000
) -> Optional[Dict[str, Any]]:
    """
    Busca todos os tickets com filtros avançados usando a Search API do GLPI.
    
    Args:
        session_token: Token da sessão
        start_date: Data inicial no formato YYYY-MM-DD (opcional)
        end_date: Data final no formato YYYY-MM-DD (opcional)
        status_filter: Filtro de status (opcional)
        entity_id: ID da entidade (opcional)
        range_start: Início da paginação (default: 0)
        range_end: Fim da paginação (default: 1000)
        
    Returns:
        Dicionário com resultados da busca ou None em caso de erro
    """
    url = f"{GLPI_BASE_URL}/search/Ticket"
    headers = {
        'Content-Type': 'application/json',
        'Session-Token': session_token,
        'App-Token': GLPI_APP_TOKEN
    }
    
    # Constrói critérios de busca
    criteria = []
    
    # Adiciona filtro de data inicial se fornecido
    if start_date:
        criteria.append({
            'link': 'AND',
            'field': 15,  # Campo de data de criação
            'searchtype': 'morethan',
            'value': start_date
        })
    
    # Adiciona filtro de data final se fornecido
    if end_date:
        criteria.append({
            'link': 'AND' if start_date else 'AND',
            'field': 15,  # Campo de data de criação
            'searchtype': 'lessthan',
            'value': end_date
        })
    
    # Adiciona filtro de status se fornecido
    if status_filter is not None:
        criteria.append({
            'link': 'AND',
            'field': 12,  # Campo de status
            'searchtype': 'equals',
            'value': str(status_filter)
        })
    
    # Adiciona filtro de entidade se fornecido
    if entity_id is not None:
        criteria.append({
            'link': 'AND',
            'field': 80,  # Campo de entidade
            'searchtype': 'equals',
            'value': entity_id
        })
    
    # Se não há critérios, adiciona um critério básico para buscar todos
    if not criteria:
        criteria.append({
            'link': 'AND',
            'field': 1,  # Campo de nome
            'searchtype': 'contains',
            'value': ''
        })
    
    # Parâmetros da requisição
    params = {
        'range': f'{range_start}-{range_end}',
        'sort': '15',  # Ordenar por data de criação
        'order': 'DESC',  # Mais recentes primeiro
        'forcedisplay[0]': '1',   # ID
        'forcedisplay[1]': '2',   # Nome
        'forcedisplay[2]': '12',  # Status
        'forcedisplay[3]': '15',  # Data criação
        'forcedisplay[4]': '16',  # Data modificação
        'forcedisplay[5]': '18',  # Usuário solicitante
        'forcedisplay[6]': '19',  # Usuário técnico
        'forcedisplay[7]': '21',  # Entidade
        'forcedisplay[8]': '82',  # ID externo
    }
    
    # Adiciona critérios aos parâmetros
    for i, criterion in enumerate(criteria):
        params[f'criteria[{i}][link]'] = criterion['link']
        params[f'criteria[{i}][field]'] = criterion['field']
        params[f'criteria[{i}][searchtype]'] = criterion['searchtype']
        params[f'criteria[{i}][value]'] = criterion['value']
    
    try:
        response = requests.get(url, headers=headers, params=params, verify=False)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Falha ao buscar tickets: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Erro ao buscar tickets: {str(e)}")
        return None


def get_all_tickets_with_history(
    session_token: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status_filter: Optional[int] = None,
    entity_id: Optional[int] = None,
    include_logs: bool = True,
    include_followups: bool = True,
    include_solutions: bool = True,
    max_tickets: int = 100
) -> List[Dict[str, Any]]:
    """
    Obtém todos os tickets com histórico completo (logs, followups, soluções).
    
    Args:
        session_token: Token da sessão
        start_date: Data inicial no formato YYYY-MM-DD (opcional)
        end_date: Data final no formato YYYY-MM-DD (opcional)
        status_filter: Filtro de status (opcional)
        entity_id: ID da entidade (opcional)
        include_logs: Incluir logs de auditoria (default: True)
        include_followups: Incluir followups (default: True)
        include_solutions: Incluir soluções (default: True)
        max_tickets: Número máximo de tickets a buscar (default: 100)
        
    Returns:
        Lista de tickets com histórico completo
    """
    logger.info(f"Buscando histórico completo de tickets (max: {max_tickets})")
    
    # Busca os tickets
    search_result = search_all_tickets(
        session_token=session_token,
        start_date=start_date,
        end_date=end_date,
        status_filter=status_filter,
        entity_id=entity_id,
        range_start=0,
        range_end=max_tickets - 1
    )
    
    if not search_result:
        logger.error("Falha ao buscar tickets")
        return []
    
    tickets_data = search_result.get('data', [])
    total_count = search_result.get('totalcount', 0)
    
    logger.info(f"Encontrados {total_count} tickets, processando {len(tickets_data)}")
    
    complete_tickets = []
    
    for ticket_dict in tickets_data:
        # Extrai o ID do ticket (pode estar em diferentes formatos)
        if isinstance(ticket_dict, dict):
            ticket_id_key = list(ticket_dict.keys())[0]
            ticket_id = ticket_dict[ticket_id_key]
        else:
            logger.warning(f"Formato de ticket inesperado: {ticket_dict}")
            continue
        
        try:
            ticket_id = int(ticket_id)
        except (ValueError, TypeError):
            logger.warning(f"ID de ticket inválido: {ticket_id}")
            continue
        
        # Obtém detalhes completos do ticket
        ticket_details = get_ticket_details(ticket_id, session_token)
        if not ticket_details:
            logger.warning(f"Não foi possível obter detalhes do ticket {ticket_id}")
            continue
        
        # Prepara o ticket completo
        complete_ticket = {
            'id': ticket_id,
            'details': ticket_details
        }
        
        # Adiciona logs se solicitado
        if include_logs:
            logs = get_ticket_logs(ticket_id, session_token)
            complete_ticket['logs'] = logs
            logger.debug(f"Ticket {ticket_id}: {len(logs)} logs encontrados")
        
        # Adiciona followups se solicitado
        if include_followups:
            followups = get_ticket_followups(ticket_id, session_token)
            complete_ticket['followups'] = followups
            logger.debug(f"Ticket {ticket_id}: {len(followups)} followups encontrados")
        
        # Adiciona soluções se solicitado
        if include_solutions:
            solutions = get_ticket_solution(ticket_id, session_token)
            complete_ticket['solutions'] = solutions
            logger.debug(f"Ticket {ticket_id}: {len(solutions)} soluções encontradas")
        
        complete_tickets.append(complete_ticket)
    
    logger.info(f"Histórico completo obtido para {len(complete_tickets)} tickets")
    return complete_tickets


# ============================================================================
# OPERAÇÕES COM USUÁRIOS
# ============================================================================

def get_user_details(user_id: int, session_token: str) -> Optional[Dict[str, Any]]:
    """
    Obtém os detalhes de um usuário específico.
    
    Args:
        user_id: ID do usuário no GLPI
        session_token: Token da sessão
        
    Returns:
        Dicionário com os detalhes do usuário ou None em caso de erro
    """
    if not user_id or user_id <= 0:
        return None
        
    url = f"{GLPI_BASE_URL}/User/{user_id}"
    headers = {
        'Content-Type': 'application/json',
        'Session-Token': session_token,
        'App-Token': GLPI_APP_TOKEN
    }
    
    try:
        response = requests.get(url, headers=headers, verify=False)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Falha ao obter detalhes do usuário {user_id}: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Erro ao obter detalhes do usuário {user_id}: {str(e)}")
        return None
