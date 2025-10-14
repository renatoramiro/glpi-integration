"""
Funções auxiliares para interação com o Supabase.

Este módulo contém funções para carregar histórico de conversas
e informações de chats do banco de dados Supabase.
"""

import os
import logging
from typing import Optional, List, Dict, Any
from supabase import create_client

# Configuração de logging
logger = logging.getLogger(__name__)

# Configurações do Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Inicializa o cliente Supabase
supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Cliente Supabase inicializado com sucesso")
    except Exception as e:
        logger.error(f"Erro ao inicializar Supabase: {str(e)}")
        supabase = None
else:
    logger.warning("Variáveis do Supabase não configuradas. Funcionalidade de histórico não estará disponível.")


def get_chat_info(user_chat_id: str) -> Optional[Dict[str, Any]]:
    """
    Busca informações de um chat específico no Supabase.
    
    Args:
        user_chat_id: ID do chat
        
    Returns:
        Dicionário com informações do chat ou None em caso de erro
    """
    if not supabase:
        logger.error("Cliente Supabase não está inicializado")
        return None
    
    try:
        result = supabase.table("chats").select("*").eq("idchat", user_chat_id).single().execute()
        if hasattr(result, 'data') and result.data:
            return result.data
        return None
    except Exception as e:
        logger.error(f"Erro ao buscar informações do chat {user_chat_id}: {str(e)}")
        return None


def get_chat_messages(user_chat_id: str) -> List[Dict[str, Any]]:
    """
    Busca todas as mensagens de um chat específico no Supabase.
    
    Args:
        user_chat_id: ID do chat
        
    Returns:
        Lista de mensagens ordenadas por data de criação
    """
    if not supabase:
        logger.error("Cliente Supabase não está inicializado")
        return []
    
    try:
        query = supabase.table("messages").select("*").eq("idchat", user_chat_id).order("createat")
        result = query.execute()
        
        # Verifica o tipo do resultado antes de acessar atributos
        messages = []
        if hasattr(result, 'data') and isinstance(result.data, list):
            messages = result.data
        elif isinstance(result, list):
            messages = result
        else:
            logger.warning(f"Formato de resposta inesperado do Supabase: {type(result)}")
        
        return messages
    except Exception as e:
        logger.error(f"Erro ao buscar mensagens do chat {user_chat_id}: {str(e)}")
        return []


def format_conversation_history(messages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Formata mensagens do Supabase para o padrão de conversation_history.
    
    Args:
        messages: Lista de mensagens do Supabase
        
    Returns:
        Lista formatada com speaker e message
    """
    conversation_history = []
    
    for msg in messages:
        if isinstance(msg, dict):
            speaker = "Cliente" if msg.get('author') == 'user' else "Eva"
            content_msg = msg.get('text', '')
            
            if not isinstance(content_msg, str):
                content_msg = str(content_msg)
            
            conversation_history.append({
                "speaker": speaker,
                "message": content_msg
            })
    
    return conversation_history


def load_chat_data(user_chat_id: str) -> Dict[str, Any]:
    """
    Carrega todas as informações de um chat (título e histórico de mensagens).
    
    Args:
        user_chat_id: ID do chat
        
    Returns:
        Dicionário com 'title' e 'conversation_history'
    """
    result = {
        'title': None,
        'conversation_history': [],
        'ticket_id': None
    }
    
    if not supabase:
        logger.error("Cliente Supabase não está inicializado")
        return result
    
    try:
        # Busca informações do chat
        chat_info = get_chat_info(user_chat_id)
        if chat_info:
            result['title'] = chat_info.get('title')
            result['ticket_id'] = chat_info.get('ticket_id')
        
        # Busca mensagens do chat
        messages = get_chat_messages(user_chat_id)
        logger.info(f"Encontradas {len(messages)} mensagens no histórico")
        
        # Formata as mensagens
        result['conversation_history'] = format_conversation_history(messages)
        logger.info(f"Histórico formatado com {len(result['conversation_history'])} mensagens")
        
        return result
    except Exception as e:
        logger.error(f"Erro ao carregar dados do chat {user_chat_id}: {str(e)}")
        return result


def update_chat_ticket_id(user_chat_id: str, ticket_id: int) -> bool:
    """
    Atualiza o ticket_id de um chat no Supabase.
    
    Args:
        user_chat_id: ID do chat
        ticket_id: ID do ticket no GLPI
        
    Returns:
        True se a atualização foi bem-sucedida, False caso contrário
    """
    if not supabase:
        logger.error("Cliente Supabase não está inicializado")
        return False
    
    try:
        # Atualiza o ticket_id do chat
        result = supabase.table("chats").update({"ticket_id": ticket_id}).eq("idchat", user_chat_id).execute()
        
        if result:
            logger.info(f"ticket_id {ticket_id} atualizado com sucesso para o chat {user_chat_id}")
            return True
        else:
            logger.error(f"Falha ao atualizar ticket_id para o chat {user_chat_id}")
            return False
    except Exception as e:
        logger.error(f"Erro ao atualizar ticket_id do chat {user_chat_id}: {str(e)}")
        return False
