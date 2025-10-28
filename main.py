import json
import logging
import os
import re
from datetime import datetime
from typing import Optional, Dict, Any, List

# Importa os helpers do GLPI e Supabase
from glpi_helper import GLPIHelper
# Importa funções específicas do supabase_helpers que são usadas
from supabase_helpers import (load_chat_data, supabase, update_chat_ticket_id,
                                get_chat_by_external_id, get_chat_by_ticket_id, save_message_to_chat)

# Configuração do logger
debug_level = logging.INFO
logger = logging.getLogger()
logger.setLevel(debug_level)

# Variáveis de ambiente
USER_TOKEN = os.getenv('USER_TOKEN')
GLPI_BASE_URL = os.getenv('GLPI_BASE_URL')
APP_TOKEN = os.getenv('APP_TOKEN')
GLPI_DB_USER = os.getenv('GLPI_DB_USER')
GLPI_DB_PASSWORD = os.getenv('GLPI_DB_PASSWORD')
GLPI_DB_NAME = os.getenv('GLPI_DB_NAME')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
SSE_BASE_URL = os.getenv('SSE_BASE_URL', 'https://sse.chatevolux.com.br')


class TicketClosedPayload:
    """Modelo para o payload de ticket fechado"""
    def __init__(self, **kwargs):
        self.ticket_id = kwargs.get('ticket_id')
        self.ticket_name = kwargs.get('ticket_name')
        self.closed_by = kwargs.get('closed_by')
        self.closed_at = kwargs.get('closed_at')
        self.solution = kwargs.get('solution')
        self.external_id = kwargs.get('external_id')
        self.additional_data = kwargs.get('additional_data', {})
        # Campos adicionais que o GLPI pode enviar
        self.id = kwargs.get('id')
        self.name = kwargs.get('name')
        self.content = kwargs.get('content')
        self.status = kwargs.get('status')
        self.users_id_lastupdater = kwargs.get('users_id_lastupdater')
        self.date_mod = kwargs.get('date_mod')


class TicketHistoryRequest:
    """Modelo para requisição de histórico de tickets"""
    def __init__(self, **kwargs):
        self.start_date = kwargs.get('start_date')
        self.end_date = kwargs.get('end_date')
        self.status_filter = kwargs.get('status_filter')
        self.entity_id = kwargs.get('entity_id')
        self.include_logs = kwargs.get('include_logs', True)
        self.include_followups = kwargs.get('include_followups', True)
        self.include_solutions = kwargs.get('include_solutions', True)
        self.max_tickets = kwargs.get('max_tickets', 100)


class CreateTicketPayload:
    """Modelo para o payload de criação de ticket"""
    def __init__(self, **kwargs):
        self.external_id = kwargs.get('external_id', '')
        self.title = kwargs.get('title', '')
        self.entity_id = kwargs.get('entity_id', 0)
        self.ticket_id = kwargs.get('ticket_id', 0)
        self.user_chat_id = kwargs.get('user_chat_id')
        self.conversation_history = kwargs.get('conversation_history', [])
        # Permite campos extras
        self.extra_fields = {k: v for k, v in kwargs.items() if k not in [
            'external_id', 'title', 'entity_id', 'ticket_id', 'user_chat_id', 'conversation_history'
        ]}



def lambda_handler(event, context):
    """
    Ponto de entrada principal para a função Lambda do AWS Serverless
    """
    logger.info(f"Evento recebido: {json.dumps(event)}")
    
    try:
        # Extrai informações do evento
        http_method = event.get('httpMethod', '')
        path = event.get('path', '')
        
        # Tratamento das diferentes rotas
        if http_method == 'POST' and path.startswith('/api/create-ticket'):
            return handle_create_ticket(event, context)
        elif http_method == 'POST' and path.startswith('/webhook/ticket-closed'):
            return handle_ticket_closed(event, context)
        elif http_method == 'POST' and path.startswith('/webhook/followup-added'):
            return handle_followup_added(event, context)
        elif http_method == 'POST' and path.startswith('/api/add-message'):
            return handle_add_message_to_ticket(event, context)
        elif http_method == 'POST' and path.startswith('/api/ticket-history'):
            return handle_ticket_history_post(event, context)
        elif http_method == 'GET' and path.startswith('/api/ticket-history'):
            return handle_ticket_history_get(event, context)
        else:
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'message': 'Rota não encontrada',
                    'path': path,
                    'method': http_method
                })
            }
    except Exception as e:
        logger.error(f"Erro não tratado: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Erro interno do servidor',
                'error': str(e)
            })
        }


def process_data(data):
    """
    Função de exemplo para processamento de dados
    """
    logger.info(f"Processando dados: {data}")
    
    # Implementação de exemplo
    result = {
        'processed': True,
        'item_count': len(data) if isinstance(data, dict) else 0,
        'timestamp': str(context) if 'context' in locals() else 'N/A'
    }
    
    return result


def send_response_to_platform(response_data: dict):
    """
    Envia a resposta do GLPI de volta para a plataforma e salva no Supabase.
    
    Args:
        response_data: Dicionário com os dados da resposta
            - ticket_id: ID do ticket no GLPI
            - external_id: ID externo (ID na plataforma)
            - followup_id: ID do followup
            - content: Conteúdo da resposta
            - user_name: Nome do consultor
            - date_creation: Data da resposta
    """
    external_id = response_data.get('external_id')
    ticket_id = response_data.get('ticket_id')
    content = response_data.get('content')
    user_name = response_data.get('user_name')
    
    logger.info(f"Enviando resposta para a plataforma:")
    logger.info(f"  External ID: {external_id}")
    logger.info(f"  Ticket ID: {ticket_id}")
    logger.info(f"  Consultor: {user_name}")
    logger.info(f"  Conteúdo: {content}")
    
    # Busca informações do chat no Supabase
    chat_info = None
    user_chat_id = None
    
    # Tenta buscar pelo external_id primeiro
    if external_id:
        logger.info(f"Buscando chat pelo external_id: {external_id}")
        chat_info = get_chat_by_external_id(external_id)
        if chat_info and isinstance(chat_info, dict):
            user_chat_id = chat_info.get('idchat')
            logger.info(f"Chat encontrado pelo external_id: {user_chat_id}")
    
    # Se não encontrou pelo external_id, tenta pelo ticket_id
    if not chat_info and ticket_id:
        logger.info(f"Buscando chat pelo ticket_id: {ticket_id}")
        chat_info = get_chat_by_ticket_id(ticket_id)
        if chat_info and isinstance(chat_info, dict):
            user_chat_id = chat_info.get('idchat')
            logger.info(f"Chat encontrado pelo ticket_id: {user_chat_id}")
    
    # Salva a mensagem no Supabase se encontrou o chat
    if user_chat_id and isinstance(user_chat_id, str) and content:
        # Formata a mensagem com o nome do consultor
        formatted_message = content
        
        # Salva a mensagem no chat
        author = user_name if user_name else "Sistema"
        success = save_message_to_chat(user_chat_id, formatted_message, author)
        if success:
            logger.info(f"Mensagem salva com sucesso no chat {user_chat_id}")
        else:
            logger.error(f"Falha ao salvar mensagem no chat {user_chat_id}")
    else:
        if not user_chat_id:
            logger.warning("Não foi possível encontrar o chat correspondente. Mensagem não salva no Supabase.")
        if not content:
            logger.warning("Conteúdo da mensagem está vazio. Mensagem não salva no Supabase.")
    
    # Por enquanto, apenas registra no log
    if not external_id:
        logger.warning("Ticket não possui external_id. Não é possível enviar para a plataforma.")
    else:
        logger.info(f"Resposta pronta para ser enviada para a plataforma (external_id: {external_id})")


def process_closed_ticket(payload: TicketClosedPayload):
    """
    Função para processar o ticket fechado.
    Implemente aqui a lógica específica da sua aplicação.
    """
    # Extrai informações do payload
    ticket_id = payload.ticket_id
    
    # Verifica se o ticket está solucionado (status 5) e salva a solução como mensagem no chat
    if payload.additional_data and payload.additional_data.get('status'):
        status = payload.additional_data.get('status')
        status_id = status.get('id') if isinstance(status, dict) else None
        
        # Se o ticket está solucionado (status 5), salva a solução como mensagem no chat
        if status_id == 5 and payload.solution and payload.additional_data:
            ticket_details = payload.additional_data.get('ticket_details')
            if ticket_details:
                external_id = ticket_details.get('externalid') or ticket_details.get('external_id')
            else:
                external_id = None
            
            if external_id and payload.solution:
                # Salva a solução como mensagem no chat
                success = save_message_to_chat(external_id, payload.solution, "Sistema")
                if success:
                    logger.info(f"Solução do ticket {ticket_id} salva como mensagem no chat {external_id}")
                    # TODO implementar fluxo do satisfatório quando ticket for solucionado
                else:
                    logger.error(f"Falha ao salvar solução do ticket {ticket_id} como mensagem no chat {external_id}")
        elif status_id == 6:
            # TODO implementar fluxo do satisfatório quando ticket for fechado
            pass
    
    # Exemplo de registro em log
    logger.info(f"Ticket {ticket_id} processado com sucesso")


def handle_ticket_history_post(event, context):
    """
    Endpoint para buscar o histórico completo de tickets do GLPI.
    
    Utiliza a API REST do GLPI para obter todos os tickets com seus respectivos
    logs de auditoria, followups e soluções, com base nos filtros fornecidos.
    """
    logger.info("Recebida requisição para buscar histórico de tickets (POST)")
    
    try:
        # Parse do body
        body = event.get('body', '{}')
        if isinstance(body, str):
            body = json.loads(body)
        
        logger.info(f"Recebida requisição para buscar histórico de tickets: {body}")
        
        # Valida o payload usando o modelo
        history_request = TicketHistoryRequest(**body)
        
        # Inicializa o helper do GLPI
        glpi_helper = GLPIHelper(
            base_url=GLPI_BASE_URL,
            user_token=USER_TOKEN,
            app_token=APP_TOKEN
        )
        
        # Inicializa a sessão
        if not glpi_helper.init_session():
            logger.error("Falha ao iniciar sessão com o GLPI")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'message': 'Falha ao conectar ao GLPI'
                })
            }
        
        try:
            # Busca o histórico completo dos tickets
            tickets_history = glpi_helper.get_all_tickets_with_history(
                start_date=history_request.start_date,
                end_date=history_request.end_date,
                status_filter=history_request.status_filter,
                entity_id=history_request.entity_id,
                include_logs=history_request.include_logs,
                include_followups=history_request.include_followups,
                include_solutions=history_request.include_solutions,
                max_tickets=history_request.max_tickets
            )
            
            # Prepara estatísticas
            total_tickets = len(tickets_history)
            total_logs = sum(len(ticket.get('logs', [])) for ticket in tickets_history)
            total_followups = sum(len(ticket.get('followups', [])) for ticket in tickets_history)
            total_solutions = sum(len(ticket.get('solutions', [])) for ticket in tickets_history)
            
            # Prepara o resumo
            summary = {
                "total_tickets": total_tickets,
                "total_logs": total_logs,
                "total_followups": total_followups,
                "total_solutions": total_solutions,
                "filters_applied": {
                    "start_date": history_request.start_date,
                    "end_date": history_request.end_date,
                    "status_filter": history_request.status_filter,
                    "entity_id": history_request.entity_id,
                    "include_logs": history_request.include_logs,
                    "include_followups": history_request.include_followups,
                    "include_solutions": history_request.include_solutions,
                    "max_tickets": history_request.max_tickets
                }
            }
            
            logger.info(f"Histórico obtido com sucesso: {total_tickets} tickets, {total_logs} logs, {total_followups} followups, {total_solutions} soluções")
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'status': 'success',
                    'message': 'Histórico de tickets obtido com sucesso',
                    'summary': summary,
                    'tickets': tickets_history
                })
            }
            
        finally:
            # Finaliza a sessão
            glpi_helper.kill_session()
        
    except Exception as e:
        logger.error(f"Erro ao buscar histórico de tickets: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': f'Erro ao buscar histórico de tickets: {str(e)}'
            })
        }


def handle_ticket_history_get(event, context):
    """
    Endpoint GET para buscar o histórico completo de tickets do GLPI.
    """
    logger.info("Recebida requisição para buscar histórico de tickets (GET)")
    
    try:
        # Extrai parâmetros de query string
        query_params = event.get('queryStringParameters', {}) or {}
        
        # Converte parâmetros para os tipos corretos
        start_date = query_params.get('start_date')
        end_date = query_params.get('end_date')
        status_filter = query_params.get('status_filter')
        entity_id = query_params.get('entity_id')
        include_logs = query_params.get('include_logs', 'true').lower() == 'true'
        include_followups = query_params.get('include_followups', 'true').lower() == 'true'
        include_solutions = query_params.get('include_solutions', 'true').lower() == 'true'
        max_tickets = int(query_params.get('max_tickets', '100'))
        
        if status_filter:
            status_filter = int(status_filter)
        if entity_id:
            entity_id = int(entity_id)
        
        logger.info(f"Recebida requisição GET para buscar histórico de tickets com parâmetros: {query_params}")
        
        # Inicializa o helper do GLPI
        glpi_helper = GLPIHelper(
            base_url=GLPI_BASE_URL,
            user_token=USER_TOKEN,
            app_token=APP_TOKEN
        )
        
        # Inicializa a sessão
        if not glpi_helper.init_session():
            logger.error("Falha ao iniciar sessão com o GLPI")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'message': 'Falha ao conectar ao GLPI'
                })
            }
        
        try:
            # Busca o histórico completo dos tickets
            tickets_history = glpi_helper.get_all_tickets_with_history(
                start_date=start_date,
                end_date=end_date,
                status_filter=status_filter,
                entity_id=entity_id,
                include_logs=include_logs,
                include_followups=include_followups,
                include_solutions=include_solutions,
                max_tickets=max_tickets
            )
            
            # Prepara estatísticas
            total_tickets = len(tickets_history)
            total_logs = sum(len(ticket.get('logs', [])) for ticket in tickets_history)
            total_followups = sum(len(ticket.get('followups', [])) for ticket in tickets_history)
            total_solutions = sum(len(ticket.get('solutions', [])) for ticket in tickets_history)
            
            # Prepara o resumo
            summary = {
                "total_tickets": total_tickets,
                "total_logs": total_logs,
                "total_followups": total_followups,
                "total_solutions": total_solutions,
                "filters_applied": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "status_filter": status_filter,
                    "entity_id": entity_id,
                    "include_logs": include_logs,
                    "include_followups": include_followups,
                    "include_solutions": include_solutions,
                    "max_tickets": max_tickets
                }
            }
            
            logger.info(f"Histórico obtido com sucesso: {total_tickets} tickets, {total_logs} logs, {total_followups} followups, {total_solutions} soluções")
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'status': 'success',
                    'message': 'Histórico de tickets obtido com sucesso',
                    'summary': summary,
                    'tickets': tickets_history
                })
            }
            
        finally:
            # Finaliza a sessão
            glpi_helper.kill_session()
        
    except Exception as e:
        logger.error(f"Erro ao buscar histórico de tickets: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': f'Erro ao buscar histórico de tickets: {str(e)}'
            })
        }


def handle_add_message_to_ticket(event, context):
    """
    Endpoint para adicionar mensagens da plataforma ao ticket do GLPI.
    
    Quando o usuário envia uma nova mensagem na plataforma, este endpoint
    busca o ticket pelo external_id ou ticket_id e adiciona a mensagem como followup.
    """
    logger.info("Recebida requisição para adicionar mensagem ao ticket")
    
    try:
        # Parse do body
        body = event.get('body', '{}')
        if isinstance(body, str):
            body = json.loads(body)
        
        logger.info(f"Recebida requisição para adicionar mensagem: {body}")
        
        external_id = body.get('external_id')
        ticket_id = body.get('ticket_id')
        message = body.get('message')
        user_name = body.get('user_name', 'Usuário')
        
        # Valida que pelo menos um identificador foi fornecido
        if not external_id and not ticket_id:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'message': 'external_id ou ticket_id é obrigatório'
                })
            }
        
        if not message:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'message': 'message é obrigatório'
                })
            }
        
        # Inicializa o helper do GLPI
        glpi_helper = GLPIHelper(
            base_url=GLPI_BASE_URL,
            user_token=USER_TOKEN,
            app_token=APP_TOKEN
        )
        
        # Inicializa a sessão
        if not glpi_helper.init_session():
            logger.error("Falha ao iniciar sessão com o GLPI")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'message': 'Falha ao conectar ao GLPI'
                })
            }
        
        try:
            # Busca o ticket pelo external_id ou ticket_id
            if ticket_id:
                # Busca diretamente pelo ID
                logger.info(f"Buscando ticket pelo ID: {ticket_id}")
                ticket_details = glpi_helper.search_ticket_by_id(ticket_id)
                if not ticket_details:
                    return {
                        'statusCode': 404,
                        'body': json.dumps({
                            'message': f'Ticket não encontrado com ID: {ticket_id}'
                        })
                    }
                # Pega o external_id se existir
                external_id = ticket_details.get('externalid') or ticket_details.get('external_id')
            else:
                # Busca pelo external_id
                logger.info(f"Buscando ticket pelo external_id: {external_id}")
                ticket_id = glpi_helper.search_ticket_by_external_id(external_id)
                if not ticket_id:
                    return {
                        'statusCode': 404,
                        'body': json.dumps({
                            'message': f'Ticket não encontrado com external_id: {external_id}'
                        })
                    }
            
            logger.info(f"Ticket encontrado: ID {ticket_id}")
            
            # Formata a mensagem com o nome do usuário
            formatted_message = f"<strong>{user_name}:</strong><br>{message}"
            
            # Adiciona o followup ao ticket
            result = glpi_helper.add_followup_to_ticket(
                ticket_id=ticket_id,
                content=formatted_message,
                is_private=0  # Público
            )
            
            if not result:
                return {
                    'statusCode': 500,
                    'body': json.dumps({
                        'message': 'Falha ao adicionar mensagem ao ticket'
                    })
                }
            
            logger.info(f"Mensagem adicionada ao ticket {ticket_id} com sucesso")
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'status': 'success',
                    'message': 'Mensagem adicionada ao ticket com sucesso',
                    'ticket_id': ticket_id,
                    'external_id': external_id,
                    'followup_id': result.get('id')
                })
            }
            
        finally:
            # Finaliza a sessão
            glpi_helper.kill_session()
        
    except Exception as e:
        logger.error(f"Erro ao adicionar mensagem ao ticket: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': f'Erro ao processar requisição: {str(e)}'
            })
        }


def handle_followup_added(event, context):
    """
    Endpoint para receber notificações quando um consultor GLPI adiciona uma resposta ao ticket.
    Este é o endpoint principal para capturar respostas do GLPI e enviar de volta para a plataforma.
    """
    logger.info("Recebida notificação de followup adicionado")
    
    try:
        # Parse do body
        body = event.get('body', '{}')
        if isinstance(body, str):
            body = json.loads(body)
        
        logger.info(f"Followup adicionado - Raw payload: {body}")
        
        # Extrai informações do followup
        followup = body.get('item', {})
        followup_id = followup.get('id')
        ticket_id = followup.get('items_id')  # ID do ticket relacionado
        followup_content = followup.get('content', '')
        
        # Remove tags HTML do conteúdo
        followup_content = re.sub(r'<[^>]+>', '', followup_content).strip()
        
        user_id = followup.get('users_id')
        date_creation = followup.get('date_creation')
        is_private = followup.get('is_private', 0)
        
        logger.info(f"Nova resposta no ticket {ticket_id}")
        logger.info(f"Followup ID: {followup_id}")
        logger.info(f"Conteúdo: {followup_content}")
        logger.info(f"Usuário: {user_id}")
        logger.info(f"Privado: {is_private}")
        
        # Inicializa o helper do GLPI
        glpi_helper = GLPIHelper(
            base_url=GLPI_BASE_URL,
            user_token=USER_TOKEN,
            app_token=APP_TOKEN
        )
        
        # Inicializa a sessão
        if not glpi_helper.init_session():
            logger.error("Falha ao iniciar sessão com o GLPI")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'message': 'Falha ao conectar ao GLPI'
                })
            }
        
        try:
            # Obtém detalhes do ticket para pegar o external_id
            ticket_details = glpi_helper.get_ticket_details(ticket_id)
            external_id = None
            
            if ticket_details:
                external_id = ticket_details.get('externalid') or ticket_details.get('external_id')
                logger.info(f"External ID do ticket: {external_id}")
            
            # Obtém informações do usuário que adicionou o followup
            user_name = "Consultor GLPI"
            if user_id:
                user_details = glpi_helper.get_user_details(user_id)
                if user_details:
                    firstname = user_details.get('firstname', '') or ''
                    realname = user_details.get('realname', '') or ''
                    name = user_details.get('name', 'Consultor GLPI') or 'Consultor GLPI'
                    user_name = f"{firstname} {realname}".strip() or name
            
            # Prepara os dados para enviar de volta para a plataforma
            response_data = {
                "ticket_id": ticket_id,
                "external_id": external_id,
                "followup_id": followup_id,
                "content": followup_content,
                "user_name": user_name,
                "user_id": user_id,
                "date_creation": date_creation,
                "is_private": is_private,
                "ticket_details": ticket_details
            }
            
            # TODO: implementar a lógica para enviar a resposta de volta para sua plataforma
            # Por exemplo:
            # - Enviar para API da plataforma usando o external_id
            # - Publicar em uma fila de mensagens
            # - Salvar em banco de dados para processamento posterior
            
            send_response_to_platform(response_data)
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'status': 'success',
                    'message': f'Resposta do ticket {ticket_id} processada com sucesso',
                    'ticket_id': ticket_id,
                    'external_id': external_id
                })
            }
            
        finally:
            # Finaliza a sessão
            glpi_helper.kill_session()
        
    except Exception as e:
        logger.error(f"Erro ao processar followup: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': f'Erro ao processar followup: {str(e)}'
            })
        }


def handle_ticket_closed(event, context):
    """
    Endpoint para receber notificações quando um ticket é fechado (status 6) 
    ou solucionado (status 5) no GLPI.
    """
    logger.info("Recebida notificação de ticket fechado/solucionado")
    
    try:
        # Parse do body
        body = event.get('body', '{}')
        if isinstance(body, str):
            body = json.loads(body)
        
        logger.info(f"Raw payload recebido: {body}")
        
        ticket = body.get('item', {})
        ticket_id = ticket.get('id')
        
        # Verifica se é um ticket fechado (status 6) ou solucionado (status 5) no GLPI
        status = ticket.get('status')
        status_id = status.get('id') if status is not None else None
        if status_id is not None and status_id not in [5, 6]:  # 5 = Solucionado, 6 = Fechado no GLPI
            logger.info(f"Ticket {ticket_id} não está fechado ou solucionado (status: {status}). Ignorando.")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'status': 'ignored',
                    'message': f'Ticket {ticket_id} não está fechado ou solucionado',
                    'ticket_id': ticket_id
                })
            }
        
        # Inicializa o helper do GLPI
        glpi_helper = GLPIHelper(
            base_url=GLPI_BASE_URL,
            user_token=USER_TOKEN,
            app_token=APP_TOKEN
        )
        
        # Inicializa a sessão
        if not glpi_helper.init_session():
            logger.error("Falha ao iniciar sessão com o GLPI")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'message': 'Falha ao conectar ao GLPI'
                })
            }
        
        try:
            # Obtém informações detalhadas do ticket
            ticket_details = glpi_helper.get_ticket_details(ticket_id)
            if ticket_details:
                logger.info(f"Detalhes do ticket {ticket_id}: {ticket_details}")
                
                ticket_name = ticket_details.get('name')
                closed_at = ticket_details.get('date_mod')
                external_id = ticket_details.get('externalid')
                
                # Obtém informações do usuário que fechou o ticket
                closed_by = "Desconhecido"
                if ticket_details.get('users_id_lastupdater'):
                    user_details = glpi_helper.get_user_details(ticket_details['users_id_lastupdater'])
                    if user_details:
                        closed_by = user_details.get('name', 'Desconhecido')
                
                # Obtém os followups (observações) do ticket
                followups = glpi_helper.get_ticket_followups(ticket_id)
                logger.info(f"Followups do ticket {ticket_id}: {followups}")
                
                # Obtém a solução do ticket
                solutions = glpi_helper.get_ticket_solution(ticket_id)
                logger.info(f"Soluções do ticket {ticket_id}: {solutions}")
                
                # Se houver soluções, pega a última
                if solutions and len(solutions) > 0:
                    last_solution = solutions[-1]
                    solution = re.sub(r'<[^>]+>', '', last_solution.get('content', '')).strip()
                else:
                    solution = ""
                
                # Atualiza o payload com as informações detalhadas
                payload_data = {
                    "ticket_id": ticket_id,
                    "ticket_name": ticket_name,
                    "closed_by": closed_by,
                    "closed_at": closed_at,
                    "solution": solution,
                    "external_id": external_id,
                    "additional_data": {
                        "status": status,
                        "ticket_details": ticket_details,
                        "followups": followups,
                        "solutions": solutions,
                        "raw_payload": body
                    }
                }
            else:
                # Extrai informações do payload (lidando com diferentes formatos do GLPI)
                ticket_id = ticket.get('id')
                ticket_name = ticket.get('name') or f"Ticket #{ticket_id}"
                closed_by = ticket.get('users_id_lastupdater') or "GLPI"
                closed_at = ticket.get('date_mod') or "Data não informada"
                solution = re.sub(r'<[^>]+>', '', body.get('solution', '')).strip()
                external_id = ticket.get('external_id', '')
                
                # Se não conseguir obter detalhes, usa os dados básicos
                payload_data = {
                    "ticket_id": ticket_id,
                    "ticket_name": ticket_name,
                    "closed_by": closed_by,
                    "closed_at": closed_at,
                    "solution": solution,
                    "external_id": external_id,
                    "additional_data": {
                        "status": status,
                        "raw_payload": body
                    }
                }
            
            # Converte para objeto TicketClosedPayload
            payload = TicketClosedPayload(**payload_data)
            
            # Aqui você pode implementar a lógica específica para lidar com o ticket fechado
            # Por exemplo:
            # - Enviar notificação por e-mail
            # - Atualizar outro sistema
            # - Registrar em um banco de dados
            
            # Exemplo de processamento
            process_closed_ticket(payload)
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'status': 'success',
                    'message': f'Ticket {ticket_id} processado com sucesso',
                    'ticket_id': ticket_id
                })
            }
            
        finally:
            # Finaliza a sessão
            glpi_helper.kill_session()
        
    except Exception as e:
        logger.error(f"Erro ao processar ticket fechado: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': f'Erro ao processar ticket: {str(e)}'
            })
        }


def handle_create_ticket(event, context):
    """
    Endpoint para criar um novo ticket no GLPI a partir de um ID da plataforma.
    """
    logger.info("Recebida requisição para criar ticket")
    
    try:
        # Parse do body
        body = event.get('body', '{}')
        if isinstance(body, str):
            body = json.loads(body)
        
        logger.info(f"Recebida requisição para criar ticket: {body}")
        
        # Verifica se temos user_chat_id
        user_chat_id = body.get('user_chat_id')
        title = None
        conversation_history = None
        ticket_id = None
        
        if user_chat_id:
            logger.info(f"Carregando informações para user_chat_id: {user_chat_id}")
            
            # Verifica se o Supabase está disponível
            if not supabase:
                logger.error("Cliente Supabase não está inicializado. Configure SUPABASE_URL e SUPABASE_KEY no .env")
                return {
                    'statusCode': 500,
                    'body': json.dumps({
                        'message': 'Serviço Supabase não configurado'
                    })
                }
            else:
                try:
                    # Carrega dados do chat usando a função auxiliar
                    chat_data = load_chat_data(user_chat_id)
                    title = chat_data.get('title')
                    ticket_id = chat_data.get('ticket_id')
                    conversation_history = chat_data.get('conversation_history', [])
                    
                except Exception as e:
                    logger.error(f"Erro ao carregar informações do Supabase: {str(e)}")
                    logger.error("Verifique se as variáveis SUPABASE_URL e SUPABASE_KEY estão corretas")
                    return {
                        'statusCode': 500,
                        'body': json.dumps({
                            'message': f'Erro ao carregar informações do chat: {str(e)}'
                        })
                    }
        
        # Valida que temos os dados necessários
        if not title:
            title = f"Ticket criado via plataforma Evolux {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
        
        if ticket_id:
            # retornar erro, pois para criar um ticket no GLPI, o ticket_id deve ser None
            logger.info(f"Ticket {ticket_id} já existe para este chat {user_chat_id}")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'message': 'Já existe um ticket associado a este chat.'
                })
            }
        
        # Valida o payload usando o modelo
        ticket_data = CreateTicketPayload(
            external_id=user_chat_id or body.get('external_id', ''),
            title=title,
            entity_id=body.get('entity_id'),
            ticket_id=ticket_id,
            user_chat_id=user_chat_id,
            conversation_history=conversation_history
        )
        
        # Inicializa o helper do GLPI
        glpi_helper = GLPIHelper(
            base_url=GLPI_BASE_URL,
            user_token=USER_TOKEN,
            app_token=APP_TOKEN
        )
        
        # Inicializa a sessão
        if not glpi_helper.init_session():
            logger.error("Falha ao iniciar sessão com o GLPI")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'message': 'Falha ao conectar ao GLPI'
                })
            }
        
        try:
            # Cria o ticket no GLPI
            result = glpi_helper.create_ticket_in_glpi(
                user_chat_id=user_chat_id,
                entity_id=ticket_data.entity_id or 0,
                conversation_history=ticket_data.conversation_history,
                title=ticket_data.title
            )
            
            if not result:
                return {
                    'statusCode': 500,
                    'body': json.dumps({
                        'message': 'Falha ao criar ticket no GLPI'
                    })
                }
            
            remote_ticket_id = result.get('id')
            logger.info(f"Ticket criado com sucesso: ID {remote_ticket_id}")
            
            # Atualiza o ticket_id do chat no Supabase
            if user_chat_id and remote_ticket_id:
                update_success = update_chat_ticket_id(user_chat_id, remote_ticket_id)
                if update_success:
                    logger.info(f"ticket_id {remote_ticket_id} atualizado com sucesso no chat {user_chat_id}")
                else:
                    logger.error(f"Falha ao atualizar ticket_id no chat {user_chat_id}")
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                },
                'body': json.dumps({
                    'status': 'success',
                    'message': 'Ticket criado com sucesso',
                    'ticket_id': remote_ticket_id,
                    'external_id': ticket_data.external_id,
                    'user_chat_id': user_chat_id,
                    'glpi_response': result
                })
            }
            
        finally:
            # Finaliza a sessão
            glpi_helper.kill_session()
        
    except Exception as e:
        logger.error(f"Erro ao criar ticket: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': f'Erro ao criar ticket: {str(e)}'
            })
        }


def handle_glpi_ticket(event, context):
    """
    Trata requisições para criação/atualização de tickets no GLPI
    """
    logger.info("Requisição para manipulação de ticket no GLPI")
    
    try:
        # Verifica se as variáveis de ambiente estão configuradas
        if not all([USER_TOKEN, GLPI_BASE_URL, APP_TOKEN]):
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'message': 'Variáveis de ambiente do GLPI não configuradas'
                })
            }
        
        # Parse do body
        body = event.get('body', '{}')
        if isinstance(body, str):
            body = json.loads(body)
        
        # Inicializa o helper do GLPI
        glpi_helper = GLPIHelper(
            base_url=GLPI_BASE_URL,
            user_token=USER_TOKEN,
            app_token=APP_TOKEN
        )
        
        # Inicializa a sessão
        if not glpi_helper.init_session():
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'message': 'Falha ao iniciar sessão com o GLPI'
                })
            }
        
        try:
            # Verifica se é criação ou atualização de ticket
            ticket_id = body.get('ticket_id')
            
            if ticket_id:
                # Atualização de ticket existente
                # Remove o ID do body antes de atualizar
                update_data = body.copy()
                update_data.pop('ticket_id', None)
                result = glpi_helper.update_ticket(ticket_id, update_data)
            else:
                # Criação de novo ticket
                result = glpi_helper.create_ticket(body)
            
            if result:
                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'application/json',
                    },
                    'body': json.dumps({
                        'message': 'Operação no ticket realizada com sucesso',
                        'result': result
                    })
                }
            else:
                return {
                    'statusCode': 500,
                    'body': json.dumps({
                        'message': 'Falha na operação com o ticket'
                    })
                }
        finally:
            # Finaliza a sessão
            glpi_helper.kill_session()
            
    except Exception as e:
        logger.error(f"Erro na manipulação de ticket do GLPI: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
            },
            'body': json.dumps({
                'message': 'Erro na manipulação de ticket do GLPI',
                'error': str(e)
            })
        }


if __name__ == "__main__":
    # Código para testar a criação de tickets no GLPI, adicionar mensagens e simular respostas do consultor
    import os
    from datetime import datetime
    import json
    
    # Configuração de logging para testes
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Carrega variáveis de ambiente do arquivo .env se existir
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("Módulo dotenv não encontrado. Configure as variáveis de ambiente manualmente.")
    
    # Configuração das variáveis de ambiente
    USER_TOKEN = os.getenv('USER_TOKEN')
    GLPI_BASE_URL = os.getenv('GLPI_BASE_URL')
    APP_TOKEN = os.getenv('APP_TOKEN')
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    
    if not all([USER_TOKEN, GLPI_BASE_URL, APP_TOKEN]):
        print("ERRO: Variáveis de ambiente não configuradas corretamente.")
        print("Configure USER_TOKEN, GLPI_BASE_URL e APP_TOKEN no arquivo .env")
        exit(1)
    
    # Verifica se as variáveis do Supabase estão configuradas
    print(f"SUPABASE_URL configurada: {bool(SUPABASE_URL)}")
    print(f"SUPABASE_KEY configurada: {bool(SUPABASE_KEY)}")
    
    # Dados para o teste de criação
    # user_chat_id = 'test-chat-id-001'
    
    # Chama a função handle_create_ticket diretamente
    ticket_id = 14
    
    # Testa simular fechamento de ticket
    print("\n=== Teste 4: Simular Fechamento de Ticket ===")
    
    # Simula o evento que seria recebido pela função handle_ticket_closed
    # Este seria o payload que o GLPI envia quando um ticket é fechado
    closed_event = {
        'body': json.dumps({
            'item': {
                'id': ticket_id,  # ID do ticket (14)
                'name': 'Ticket de teste para fechamento',
                'status': {
                    'id': 5,  # 6 = Fechado no GLPI
                    'name': 'Solucionado'
                },
                'users_id_lastupdater': 2,  # ID do usuário que fechou
                'date_mod': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'external_id': 'df6274cb-fa3d-46b3-87bb-f5bd2ea0013b',
                'solution': '<p>Problema resolvido. Era apenas uma configuração incorreta.</p>'
            }
        })
    }
    
    try:
        result = handle_ticket_closed(closed_event, {})
        print(f"Resultado do processamento do fechamento do ticket: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        if result.get('statusCode') == 200:
            print("Fechamento do ticket processado com sucesso!")
        else:
            print(f"Falha ao processar fechamento do ticket. Status code: {result.get('statusCode')}")
            body = json.loads(result.get('body', '{}'))
            print(f"Mensagem: {body.get('message', 'Erro desconhecido')}")
    except Exception as e:
        print(f"ERRO durante o processamento do fechamento do ticket: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n=== Todos os testes concluídos! ===")
