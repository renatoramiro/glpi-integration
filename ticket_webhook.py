from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json
import logging
import requests
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Configurações do GLPI
GLPI_BASE_URL = os.getenv("GLPI_BASE_URL", "http://localhost:8080/apirest.php")
GLPI_USER_TOKEN = os.getenv("USER_TOKEN", "")
GLPI_APP_TOKEN = os.getenv("APP_TOKEN", "")

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="GLPI Ticket Webhook", description="Webhook para receber notificações de tickets fechados no GLPI")

def init_glpi_session():
    """
    Inicializa uma sessão com o GLPI
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

def get_ticket_details(ticket_id: int, session_token: str):
    """
    Obtém os detalhes de um ticket específico
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

def get_user_details(user_id: int, session_token: str):
    """
    Obtém os detalhes de um usuário específico
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

def get_ticket_followups(ticket_id: int, session_token: str):
    """
    Obtém os followups (observações) de um ticket específico
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

def get_ticket_solution(ticket_id: int, session_token: str):
    """
    Obtém a solução de um ticket específico
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

def kill_glpi_session(session_token: str):
    """
    Finaliza a sessão com o GLPI
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

class TicketClosedPayload(BaseModel):
    """Modelo para o payload de ticket fechado"""
    ticket_id: Optional[int] = None
    ticket_name: Optional[str] = None
    closed_by: Optional[str] = None
    closed_at: Optional[str] = None
    solution: Optional[str] = None
    requester_email: Optional[str] = None
    requester_name: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None
    
    # Campos adicionais que o GLPI pode enviar
    id: Optional[int] = None
    name: Optional[str] = None
    content: Optional[str] = None
    status: Optional[int] = None
    users_id_lastupdater: Optional[int] = None
    date_mod: Optional[str] = None
    _users_id_requester: Optional[int] = None
    # Permite campos extras
    class Config:
        extra = "allow"

@app.post("/webhook/ticket-closed", summary="Endpoint para tickets fechados")
async def handle_ticket_closed(request: Request):
    """
    Endpoint para receber notificações quando um ticket é fechado no GLPI.
    
    Este endpoint pode ser configurado como webhook no GLPI para receber
    notificações em tempo real quando tickets forem fechados.
    """
    try:
        # Captura o payload bruto
        raw_payload = await request.json()
        logger.info(f"Raw payload recebido: {raw_payload}")
        
        ticket = raw_payload.get('item')
        
        # Extrai informações do payload (lidando com diferentes formatos do GLPI)
        ticket_id = ticket.get('id')
        ticket_name = ticket.get('name') or f"Ticket #{ticket_id}"
        closed_by = ticket.get('users_id_lastupdater') or "GLPI"
        closed_at = ticket.get('date_mod') or "Data não informada"
        solution = raw_payload.get('solution', '')
        requester_email = raw_payload.get('requester_email', '')
        requester_name = raw_payload.get('requester_name', '')
        
        # Verifica se é um ticket fechado (status 6 no GLPI)
        status = ticket.get('status')
        if status is not None and status.get('id') != 6:  # 6 = Fechado no GLPI
            logger.info(f"Ticket {ticket_id} não está fechado (status: {status}). Ignorando.")
            return {
                "status": "ignored",
                "message": f"Ticket {ticket_id} não está fechado",
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
                
                # Obtém informações do usuário que fechou o ticket
                if ticket_details.get('users_id_lastupdater'):
                    user_details = get_user_details(ticket_details['users_id_lastupdater'], session_token)
                    if user_details:
                        closed_by = f"{user_details.get('firstname', '')} {user_details.get('realname', '')}".strip() or user_details.get('name', 'Desconhecido')
                
                # Obtém informações do solicitante
                if ticket_details.get('_users_id_requester'):
                    requester_details = get_user_details(ticket_details['_users_id_requester'], session_token)
                    if requester_details:
                        requester_name = f"{requester_details.get('firstname', '')} {requester_details.get('realname', '')}".strip() or requester_details.get('name', 'Desconhecido')
                        requester_email = requester_details.get('email', '')
                
                # Obtém os followups (observações) do ticket
                followups = get_ticket_followups(ticket_id, session_token)
                logger.info(f"Followups do ticket {ticket_id}: {followups}")
                
                # Obtém a solução do ticket
                solutions = get_ticket_solution(ticket_id, session_token)
                logger.info(f"Soluções do ticket {ticket_id}: {solutions}")
                
                # Atualiza as informações com os dados reais
                ticket_name = ticket_details.get('name', ticket_name)
                solution = ticket_details.get('solution', solution)
                closed_at = ticket_details.get('date_mod', closed_at)
                
                # Se houver soluções, pega a última
                if solutions and len(solutions) > 0:
                    last_solution = solutions[-1]
                    solution = last_solution.get('content', solution)
                
                # Atualiza o payload com as informações detalhadas
                payload_data = {
                    "ticket_id": ticket_id,
                    "ticket_name": ticket_name,
                    "closed_by": closed_by,
                    "closed_at": closed_at,
                    "solution": solution,
                    "requester_email": requester_email,
                    "requester_name": requester_name,
                    "additional_data": {
                        "status": status,
                        "ticket_details": ticket_details,
                        "followups": followups,
                        "solutions": solutions,
                        "raw_payload": raw_payload
                    }
                }
            else:
                # Se não conseguir obter detalhes, usa os dados básicos
                payload_data = {
                    "ticket_id": ticket_id,
                    "ticket_name": ticket_name,
                    "closed_by": closed_by,
                    "closed_at": closed_at,
                    "solution": solution,
                    "requester_email": requester_email,
                    "requester_name": requester_name,
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
    Envia a resposta do consultor de volta para a plataforma.
    
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
    content = response_data.get('content')
    user_name = response_data.get('user_name')
    
    logger.info(f"Enviando resposta para a plataforma:")
    logger.info(f"  External ID: {external_id}")
    logger.info(f"  Consultor: {user_name}")
    logger.info(f"  Conteúdo: {content}")
    
    # IMPLEMENTAR AQUI: Enviar para sua plataforma
    # Exemplo de implementação:
    # 
    # if external_id:
    #     platform_api_url = "https://sua-plataforma.com/api/messages"
    #     payload = {
    #         "conversation_id": external_id,
    #         "message": content,
    #         "sender": user_name,
    #         "sender_type": "agent"
    #     }
    #     
    #     response = requests.post(platform_api_url, json=payload)
    #     if response.status_code == 200:
    #         logger.info(f"Resposta enviada com sucesso para a plataforma")
    #     else:
    #         logger.error(f"Falha ao enviar resposta: {response.status_code}")
    
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
    ticket_name = payload.ticket_name
    closed_by = payload.closed_by
    closed_at = payload.closed_at
    
    # Exemplo de processamento
    logger.info(f"Processando ticket fechado #{ticket_id}")
    logger.info(f"Nome: {ticket_name}")
    logger.info(f"Fechado por: {closed_by}")
    logger.info(f"Data de fechamento: {closed_at}")
    
    if payload.solution:
        logger.info(f"Solução: {payload.solution}")
    
    if payload.requester_email:
        logger.info(f"Solicitante: {payload.requester_name} <{payload.requester_email}>")
    
    # Mostra informações adicionais se disponíveis
    if payload.additional_data:
        ticket_details = payload.additional_data.get('ticket_details')
        if ticket_details:
            logger.info(f"Categoria: {ticket_details.get('itilcategories_id', 'Não informada')}")
            logger.info(f"Prioridade: {ticket_details.get('priority', 'Não informada')}")
            logger.info(f"Entidade: {ticket_details.get('entities_id', 'Não informada')}")
        
        # Mostra os followups (observações)
        followups = payload.additional_data.get('followups', [])
        if followups:
            logger.info(f"Número de observações: {len(followups)}")
            for i, followup in enumerate(followups, 1):
                logger.info(f"Observação {i}:")
                logger.info(f"  - Conteúdo: {followup.get('content', 'N/A')}")
                logger.info(f"  - Data: {followup.get('date_creation', 'N/A')}")
                logger.info(f"  - Usuário: {followup.get('users_id', 'N/A')}")
        
        # Mostra as soluções
        solutions = payload.additional_data.get('solutions', [])
        if solutions:
            logger.info(f"Número de soluções: {len(solutions)}")
            for i, sol in enumerate(solutions, 1):
                logger.info(f"Solução {i}:")
                logger.info(f"  - Conteúdo: {sol.get('content', 'N/A')}")
                logger.info(f"  - Data: {sol.get('date_creation', 'N/A')}")
    
    # Aqui você pode adicionar sua lógica específica, como:
    # - Enviar e-mail de notificação
    # - Atualizar CRM
    # - Registrar em sistema de relatórios
    # - Etc.
    
    # Exemplo de registro em log
    logger.info(f"Ticket {ticket_id} processado com sucesso")

@app.get("/health", summary="Health check")
async def health_check():
    """
    Endpoint de health check para verificar se o serviço está ativo.
    """
    return {"status": "healthy", "service": "GLPI Ticket Webhook"}

@app.post("/webhook/ticket-updated", summary="Endpoint para tickets atualizados")
async def handle_ticket_updated(request: Request):
    """
    Endpoint genérico para receber notificações de atualização de tickets.
    """
    try:
        payload = await request.json()
        logger.info(f"Ticket atualizado recebido: {payload}")
        
        # Processar a atualização do ticket
        # Implemente sua lógica aqui
        
        return {
            "status": "success",
            "message": "Atualização de ticket recebida e processada",
            "data": payload
        }
    except Exception as e:
        logger.error(f"Erro ao processar atualização de ticket: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar atualização: {str(e)}")

@app.post("/webhook/followup-added", summary="Endpoint para novas respostas do consultor")
async def handle_followup_added(request: Request):
    """
    Endpoint para receber notificações quando um consultor adiciona uma resposta ao ticket.
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
                    user_name = f"{user_details.get('firstname', '')} {user_details.get('realname', '')}".strip() or user_details.get('name', 'Consultor GLPI')
            
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
            
            # Aqui você deve implementar a lógica para enviar a resposta de volta para sua plataforma
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
