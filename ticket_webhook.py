import os
import logging
from datetime import datetime
from pydantic import BaseModel
from dotenv import load_dotenv
import logging
import re
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Request

from glpi_helpers import (init_glpi_session,
                        kill_glpi_session,
                        get_ticket_details,
                        get_user_details,
                        get_ticket_followups,
                        get_ticket_solution,
                        create_ticket_in_glpi,
                        add_followup_to_ticket,
                        search_ticket_by_id,
                        search_ticket_by_external_id,
                        get_ticket_logs,
                        search_all_tickets,
                        get_all_tickets_with_history)
from supabase_helpers import (load_chat_data, supabase, update_chat_ticket_id,
                              get_chat_by_external_id, get_chat_by_ticket_id, save_message_to_chat)

load_dotenv()

# Configurações do GLPI
GLPI_BASE_URL = os.getenv("GLPI_BASE_URL", "http://localhost:8080/apirest.php")
GLPI_USER_TOKEN = os.getenv("USER_TOKEN", "")
GLPI_APP_TOKEN = os.getenv("APP_TOKEN", "")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE")
# UUID_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
SSE_BASE_URL = os.environ.get('SSE_BASE_URL', 'https://sse.chatevolux.com.br')

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="GLPI Ticket Webhook", description="Webhook para receber notificações de tickets fechados no GLPI") 

class TicketClosedPayload(BaseModel):
    """Modelo para o payload de ticket fechado"""
    ticket_id: Optional[int] = None
    ticket_name: Optional[str] = None
    closed_by: Optional[str] = None
    closed_at: Optional[str] = None
    solution: Optional[str] = None
    external_id: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None
    
    # Campos adicionais que o GLPI pode enviar
    id: Optional[int] = None
    name: Optional[str] = None
    content: Optional[str] = None
    status: Optional[int] = None
    users_id_lastupdater: Optional[int] = None
    date_mod: Optional[str] = None
    # Permite campos extras
    class Config:
        extra = "allow"

class TicketHistoryRequest(BaseModel):
    """Modelo para requisição de histórico de tickets"""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status_filter: Optional[int] = None
    entity_id: Optional[int] = None
    include_logs: bool = True
    include_followups: bool = True
    include_solutions: bool = True
    max_tickets: int = 100

class CreateTicketPayload(BaseModel):
    """Modelo para o payload de criação de ticket"""
    external_id: str
    title: str
    entity_id: Optional[int] = 0
    ticket_id: Optional[int] = 0
    user_chat_id: Optional[str] = None  # ID do chat para carregar histórico
    conversation_history: Optional[list] = None
    # Permite campos extras
    class Config:
        extra = "allow"

@app.post("/api/create-ticket", summary="Cria um novo ticket no GLPI")
async def create_ticket(request: Request):
    """
    Endpoint para criar um novo ticket no GLPI a partir de um ID da plataforma.
    
    Payload esperado (campos obrigatórios marcados com *):
    {
        "user_chat_id": "chat-12345",  // ID do chat para carregar titulo e histórico de mensagens
    }
    
    Pelo menos um dos seguintes conjuntos deve ser fornecido:
    - user_chat_id (para carregar title e histórico de mensagens)
    """

    try:
        # Captura o payload
        payload = await request.json()
        logger.info(f"Recebida requisição para criar ticket: {payload}")
        
        # Verifica se temos user_chat_id
        user_chat_id = payload.get('user_chat_id')
        title = None
        conversation_history = None
        ticket_id = None
        
        if user_chat_id:
            logger.info(f"Carregando informações para user_chat_id: {user_chat_id}")
            
            # Verifica se o Supabase está disponível
            if not supabase:
                logger.error("Cliente Supabase não está inicializado. Configure SUPABASE_URL e SUPABASE_KEY no .env")
                raise HTTPException(status_code=500, detail="Serviço Supabase não configurado")
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
                    raise HTTPException(status_code=500, detail=f"Erro ao carregar informações do chat: {str(e)}")
        
        # Valida que temos os dados necessários
        if not title:
            title = f"Ticket criado via plataforma Evolux {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"

        if ticket_id:
            # retornar erro, pois para criar um ticket no GLPI, o ticket_id deve ser None
            logger.info(f"Ticket {ticket_id} já existe para este chat {user_chat_id}")
            raise HTTPException(status_code=400, detail="Já existe um ticket associado a este chat.")
        
        # Valida o payload usando o modelo Pydantic
        ticket_data = CreateTicketPayload(
            external_id=user_chat_id or payload.get('external_id', ''),
            title=title,
            entity_id=payload.get('entity_id', None),
            ticket_id=ticket_id,
            user_chat_id=user_chat_id,
            conversation_history=conversation_history
        )
        
        # Inicializa sessão com o GLPI
        session_token = init_glpi_session()
        if not session_token:
            logger.error("Falha ao iniciar sessão com o GLPI")
            raise HTTPException(status_code=500, detail="Falha ao conectar ao GLPI")
        
        try:
            # Cria o ticket no GLPI
            result = create_ticket_in_glpi(
                title=ticket_data.title,
                external_id=ticket_data.external_id,
                session_token=session_token,
                entity_id=ticket_data.entity_id or 0,
                conversation_history=conversation_history
            )
            
            if not result:
                raise HTTPException(
                    status_code=500,
                    detail="Falha ao criar ticket no GLPI"
                )
            
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
                "status": "success",
                "message": "Ticket criado com sucesso",
                "ticket_id": remote_ticket_id,
                "external_id": ticket_data.external_id,
                "user_chat_id": user_chat_id,
                "glpi_response": result
            }
            
        finally:
            # Finaliza a sessão com o GLPI
            kill_glpi_session(session_token)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Erro ao criar ticket: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao criar ticket: {str(e)}")

@app.post("/webhook/ticket-closed", summary="Endpoint para tickets fechados/solucionados")
async def handle_ticket_closed(request: Request):
    """
    Endpoint para receber notificações quando um ticket é fechado (status 6) 
    ou solucionado (status 5) no GLPI.
    
    Este endpoint pode ser configurado como webhook no GLPI para receber
    notificações em tempo real quando tickets forem fechados ou solucionados.
    """
    try:
        # Captura o payload bruto
        raw_payload = await request.json()
        logger.info(f"Raw payload recebido: {raw_payload}")
        
        ticket = raw_payload.get('item')
        ticket_id = ticket.get('id')
        
        # Verifica se é um ticket fechado (status 6) ou solucionado (status 5) no GLPI
        status = ticket.get('status')
        status_id = status.get('id') if status is not None else None
        if status_id is not None and status_id not in [5, 6]:  # 5 = Solucionado, 6 = Fechado no GLPI
            logger.info(f"Ticket {ticket_id} não está fechado ou solucionado (status: {status}). Ignorando.")
            return {
                "status": "ignored",
                "message": f"Ticket {ticket_id} não está fechado ou solucionado",
                "ticket_id": ticket_id
            }
        
        # Inicializa sessão com o GLPI para obter informações detalhadas
        session_token = init_glpi_session()
        if not session_token:
            logger.error("Falha ao iniciar sessão com o GLPI")
            raise HTTPException(status_code=500, detail="Falha ao conectar ao GLPI")
        
        try:
            # Obtém informações detalhadas do ticket
            ticket_details = get_ticket_details(ticket_id, session_token)
            if ticket_details:
                logger.info(f"Detalhes do ticket {ticket_id}: {ticket_details}")

                ticket_name = ticket_details.get('name')
                closed_at = ticket_details.get('date_mod')
                external_id = ticket_details.get('externalid')
                
                # Obtém informações do usuário que fechou o ticket
                closed_by = "Desconhecido"
                if ticket_details.get('users_id_lastupdater'):
                    user_details = get_user_details(ticket_details['users_id_lastupdater'], session_token)
                    if user_details:
                        closed_by = user_details.get('name', 'Desconhecido')
                
                # Obtém os followups (observações) do ticket
                followups = get_ticket_followups(ticket_id, session_token)
                logger.info(f"Followups do ticket {ticket_id}: {followups}")
                
                # Obtém a solução do ticket
                solutions = get_ticket_solution(ticket_id, session_token)
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
                        "raw_payload": raw_payload
                    }
                }
            else:
                # Extrai informações do payload (lidando com diferentes formatos do GLPI)
                ticket_id = ticket.get('id')
                ticket_name = ticket.get('name') or f"Ticket #{ticket_id}"
                closed_by = ticket.get('users_id_lastupdater') or "GLPI"
                closed_at = ticket.get('date_mod') or "Data não informada"
                solution = re.sub(r'<[^>]+>', '', raw_payload.get('solution', '')).strip()
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
                        "raw_payload": raw_payload
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
            
        finally:
            # Finaliza a sessão com o GLPI
            kill_glpi_session(session_token)
        
        return {
            "status": "success",
            "message": f"Ticket {ticket_id} processado com sucesso",
            "ticket_id": ticket_id
        }
    except Exception as e:
        logger.error(f"Erro ao processar ticket fechado: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar ticket: {str(e)}")
        
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

@app.get("/health", summary="Health check")
async def health_check():
    """
    Endpoint de health check para verificar se o serviço está ativo.
    """
    return {"status": "healthy", "service": "GLPI Ticket Webhook"}

@app.post("/webhook/followup-added", summary="Endpoint para novas respostas do consultor GLPI")
async def handle_followup_added(request: Request):
    """
    Endpoint para receber notificações quando um consultor GLPI adiciona uma resposta ao ticket.
    Este é o endpoint principal para capturar respostas do GLPI e enviar de volta para a plataforma.
    """
    try:
        # Captura o payload bruto
        raw_payload = await request.json()
        logger.info(f"Followup adicionado - Raw payload: {raw_payload}")
        
        # Extrai informações do followup
        followup = raw_payload.get('item', {})
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
        
        # Inicializa sessão com o GLPI para obter informações detalhadas
        session_token = init_glpi_session()
        if not session_token:
            logger.error("Falha ao iniciar sessão com o GLPI")
            raise HTTPException(status_code=500, detail="Falha ao conectar ao GLPI")
        
        try:
            # Obtém detalhes do ticket para pegar o external_id
            ticket_details = get_ticket_details(ticket_id, session_token)
            external_id = None
            
            if ticket_details:
                external_id = ticket_details.get('externalid') or ticket_details.get('external_id')
                logger.info(f"External ID do ticket: {external_id}")
            
            # Obtém informações do usuário que adicionou o followup
            user_name = "Consultor GLPI"
            if user_id:
                user_details = get_user_details(user_id, session_token)
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
            
        finally:
            # Finaliza a sessão com o GLPI
            kill_glpi_session(session_token)
        
        return {
            "status": "success",
            "message": f"Resposta do ticket {ticket_id} processada com sucesso",
            "ticket_id": ticket_id,
            "external_id": external_id
        }
    except Exception as e:
        logger.error(f"Erro ao processar followup: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar followup: {str(e)}")

@app.post("/api/add-message", summary="Adiciona mensagem da plataforma ao ticket do GLPI")
async def add_message_to_ticket(request: Request):
    """
    Endpoint para adicionar mensagens da plataforma ao ticket do GLPI.
    
    Quando o usuário envia uma nova mensagem na plataforma, este endpoint
    busca o ticket pelo external_id ou ticket_id e adiciona a mensagem como followup.
    
    Payload esperado:
    {
        "external_id": "CONV-12345",  // OU
        "ticket_id": 20,              // Usar um dos dois
        "message": "Mensagem do usuário",
        "user_name": "Nome do Usuário" (opcional)
    }
    """
    try:
        # Captura o payload
        payload = await request.json()
        logger.info(f"Recebida requisição para adicionar mensagem: {payload}")
        
        external_id = payload.get('external_id')
        ticket_id = payload.get('ticket_id')
        message = payload.get('message')
        user_name = payload.get('user_name', 'Usuário')
        
        # Valida que pelo menos um identificador foi fornecido
        if not external_id and not ticket_id:
            raise HTTPException(
                status_code=400, 
                detail="external_id ou ticket_id é obrigatório"
            )
        
        if not message:
            raise HTTPException(status_code=400, detail="message é obrigatório")
        
        # Inicializa sessão com o GLPI
        session_token = init_glpi_session()
        if not session_token:
            logger.error("Falha ao iniciar sessão com o GLPI")
            raise HTTPException(status_code=500, detail="Falha ao conectar ao GLPI")
        
        try:
            # Busca o ticket pelo external_id ou ticket_id
            if ticket_id:
                # Busca diretamente pelo ID
                logger.info(f"Buscando ticket pelo ID: {ticket_id}")
                ticket_details = search_ticket_by_id(ticket_id, session_token)
                if not ticket_details:
                    raise HTTPException(
                        status_code=404, 
                        detail=f"Ticket não encontrado com ID: {ticket_id}"
                    )
                # Pega o external_id se existir
                external_id = ticket_details.get('externalid') or ticket_details.get('external_id')
            else:
                # Busca pelo external_id
                logger.info(f"Buscando ticket pelo external_id: {external_id}")
                ticket_id = search_ticket_by_external_id(external_id, session_token)
                if not ticket_id:
                    raise HTTPException(
                        status_code=404, 
                        detail=f"Ticket não encontrado com external_id: {external_id}"
                    )
            
            logger.info(f"Ticket encontrado: ID {ticket_id}")
            
            # Formata a mensagem com o nome do usuário
            formatted_message = f"<strong>{user_name}:</strong><br>{message}"
            
            # Adiciona o followup ao ticket
            result = add_followup_to_ticket(
                ticket_id=ticket_id,
                content=formatted_message,
                session_token=session_token,
                is_private=0  # Público
            )
            
            if not result:
                raise HTTPException(
                    status_code=500,
                    detail="Falha ao adicionar mensagem ao ticket"
                )
            
            logger.info(f"Mensagem adicionada ao ticket {ticket_id} com sucesso")
            
            return {
                "status": "success",
                "message": "Mensagem adicionada ao ticket com sucesso",
                "ticket_id": ticket_id,
                "external_id": external_id,
                "followup_id": result.get('id')
            }
            
        finally:
            # Finaliza a sessão com o GLPI
            kill_glpi_session(session_token)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao adicionar mensagem ao ticket: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar requisição: {str(e)}")

@app.post("/api/ticket-history", summary="Busca histórico completo de tickets")
async def get_ticket_history(request: Request):
    """
    Endpoint para buscar o histórico completo de tickets do GLPI.
    
    Utiliza a API REST do GLPI para obter todos os tickets com seus respectivos
    logs de auditoria, followups e soluções, com base nos filtros fornecidos.
    
    Payload esperado (opcional):
    {
        "start_date": "2025-01-01",        // Data inicial (opcional)
        "end_date": "2025-12-31",          // Data final (opcional)
        "status_filter": 5,                // Filtro de status (opcional)
        "entity_id": 0,                    // ID da entidade (opcional)
        "include_logs": true,              // Incluir logs de auditoria
        "include_followups": true,         // Incluir followups
        "include_solutions": true,         // Incluir soluções
        "max_tickets": 100                 // Número máximo de tickets
    }
    
    Exemplo de uso:
    curl -X POST http://localhost:8000/api/ticket-history \
         -H "Content-Type: application/json" \
         -d '{"start_date": "2025-01-01", "max_tickets": 50}'
    """
    try:
        # Captura o payload
        payload = await request.json()
        logger.info(f"Recebida requisição para buscar histórico de tickets: {payload}")
        
        # Valida o payload usando o modelo Pydantic
        history_request = TicketHistoryRequest(**payload)
        
        # Inicializa sessão com o GLPI
        session_token = init_glpi_session()
        if not session_token:
            logger.error("Falha ao iniciar sessão com o GLPI")
            raise HTTPException(status_code=500, detail="Falha ao conectar ao GLPI")
        
        try:
            # Busca o histórico completo dos tickets
            tickets_history = get_all_tickets_with_history(
                session_token=session_token,
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
                "status": "success",
                "message": "Histórico de tickets obtido com sucesso",
                "summary": summary,
                "tickets": tickets_history
            }
            
        finally:
            # Finaliza a sessão com o GLPI
            kill_glpi_session(session_token)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar histórico de tickets: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao buscar histórico de tickets: {str(e)}")

@app.get("/api/ticket-history", summary="Busca histórico completo de tickets (GET)")
async def get_ticket_history_get(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status_filter: Optional[int] = None,
    entity_id: Optional[int] = None,
    include_logs: bool = True,
    include_followups: bool = True,
    include_solutions: bool = True,
    max_tickets: int = 100
):
    """
    Endpoint GET para buscar o histórico completo de tickets do GLPI.
    
    Parâmetros de query:
    - start_date: Data inicial no formato YYYY-MM-DD (opcional)
    - end_date: Data final no formato YYYY-MM-DD (opcional)
    - status_filter: Filtro de status (opcional)
    - entity_id: ID da entidade (opcional)
    - include_logs: Incluir logs de auditoria (default: true)
    - include_followups: Incluir followups (default: true)
    - include_solutions: Incluir soluções (default: true)
    - max_tickets: Número máximo de tickets (default: 100)
    
    Exemplo de uso:
    curl -X GET "http://localhost:8000/api/ticket-history?start_date=2025-01-01&max_tickets=50"
    """
    try:
        logger.info(f"Recebida requisição GET para buscar histórico de tickets com parâmetros: {locals()}")
        
        # Inicializa sessão com o GLPI
        session_token = init_glpi_session()
        if not session_token:
            logger.error("Falha ao iniciar sessão com o GLPI")
            raise HTTPException(status_code=500, detail="Falha ao conectar ao GLPI")
        
        try:
            # Busca o histórico completo dos tickets
            tickets_history = get_all_tickets_with_history(
                session_token=session_token,
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
                "status": "success",
                "message": "Histórico de tickets obtido com sucesso",
                "summary": summary,
                "tickets": tickets_history
            }
            
        finally:
            # Finaliza a sessão com o GLPI
            kill_glpi_session(session_token)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar histórico de tickets: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao buscar histórico de tickets: {str(e)}")

@app.post("/webhook/debug", summary="Endpoint de debug para capturar qualquer payload")
async def debug_webhook(request: Request):
    """
    Endpoint de debug para capturar exatamente o que está sendo enviado pelo GLPI.
    """
    try:
        # Captura o payload bruto
        raw_body = await request.body()
        headers = dict(request.headers)
        
        logger.info(f"=== DEBUG WEBHOOK ===")
        logger.info(f"Headers: {headers}")
        logger.info(f"Raw body: {raw_body}")
        
        # Tenta parsear como JSON
        try:
            json_payload = await request.json()
            logger.info(f"JSON payload: {json_payload}")
        except:
            logger.info("Não foi possível parsear como JSON")
            json_payload = None
        
        return {
            "status": "debugged",
            "headers": headers,
            "raw_body": raw_body.decode('utf-8') if raw_body else "",
            "json_payload": json_payload
        }
    except Exception as e:
        logger.error(f"Erro no debug webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro no debug: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
