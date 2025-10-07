#!/usr/bin/env python3
"""
Exemplo de como criar um ticket no GLPI com ID externo.
"""

import requests
import os
from dotenv import load_dotenv

def create_ticket_with_external_id(base_url, app_token, session_token, external_id, ticket_info):
    """
    Cria um ticket no GLPI com ID externo.
    
    Args:
        base_url: URL base da API do GLPI
        app_token: Token da aplicação
        session_token: Token da sessão
        external_id: ID externo do ticket (ex: ID de outro sistema)
        ticket_info: Dicionário com informações do ticket
    
    Returns:
        Dicionário com informações do ticket criado
    """
    url = f"{base_url}/Ticket"
    headers = {
        'Content-Type': 'application/json',
        'Session-Token': session_token,
        'App-Token': app_token
    }
    
    # Dados do ticket incluindo o ID externo
    ticket_data = {
        'name': ticket_info.get('name', 'Ticket sem título'),
        'content': ticket_info.get('content', ''),
        'entities_id': ticket_info.get('entities_id', 0),
        'externalid': external_id,
        # Outros campos opcionais
        'type': ticket_info.get('type', 1),  # 1 = Incidente, 2 = Requisição
        'urgency': ticket_info.get('urgency', 3),  # 1-5 (1=Muito baixa, 5=Muito alta)
        'impact': ticket_info.get('impact', 3),  # 1-5
        'priority': ticket_info.get('priority', 3),  # 1-6
        'itilcategories_id': ticket_info.get('category_id', 0),  # ID da categoria
        'requesttypes_id': ticket_info.get('request_type_id', 1),  # Origem da requisição
    }
    
    payload = {
        'input': ticket_data
    }
    
    response = requests.post(url, headers=headers, json=payload, verify=False)
    if response.status_code in [200, 201]:
        return response.json()
    else:
        raise Exception(f"Falha ao criar ticket: {response.status_code} - {response.text}")

def init_session(base_url, app_token, user_token):
    """Inicializa uma sessão com o GLPI"""
    url = f"{base_url}/initSession"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'user_token {user_token}',
        'App-Token': app_token
    }
    
    response = requests.get(url, headers=headers, verify=False)
    if response.status_code == 200:
        return response.json()['session_token']
    else:
        raise Exception(f"Falha ao iniciar sessão: {response.status_code} - {response.text}")

def kill_session(base_url, app_token, session_token):
    """Finaliza a sessão com o GLPI"""
    url = f"{base_url}/killSession"
    headers = {
        'Content-Type': 'application/json',
        'Session-Token': session_token,
        'App-Token': app_token
    }
    
    response = requests.get(url, headers=headers, verify=False)
    return response.status_code == 200

def main():
    # Carrega as variáveis de ambiente
    load_dotenv()
    
    user_token = os.getenv("USER_TOKEN")
    base_url = os.getenv("GLPI_BASE_URL")
    app_token = os.getenv("APP_TOKEN")
    
    print(f"Conectando ao GLPI em: {base_url}")
    
    session_token = None
    
    try:
        # Inicializa a sessão
        session_token = init_session(base_url, app_token, user_token)
        print("Sessão iniciada com sucesso!")
        
        # ID externo - pode ser o ID de outro sistema (CRM, ERP, etc.)
        external_id = "SISTEMA_EXTERNO_12345"
        
        # Informações do ticket
        ticket_info = {
            'name': 'Ticket com ID Externo',
            'content': 'Este ticket foi criado com um ID externo para rastreamento em outro sistema.',
            'entities_id': 0,  # Entidade raiz
            'type': 1,  # Incidente
            'urgency': 3,  # Média
            'impact': 3,  # Médio
            'priority': 3,  # Média
        }
        
        # Cria o ticket com ID externo
        result = create_ticket_with_external_id(
            base_url, 
            app_token, 
            session_token, 
            external_id, 
            ticket_info
        )
        
        print(f"\n✅ Ticket criado com sucesso!")
        print(f"ID do ticket no GLPI: {result['id']}")
        print(f"ID externo: {external_id}")
        print(f"Mensagem: {result.get('message', 'N/A')}")
        
    except Exception as e:
        print(f"\n❌ Erro: {str(e)}")
    
    finally:
        # Finaliza a sessão se ela foi criada
        if session_token:
            if kill_session(base_url, app_token, session_token):
                print("\nSessão encerrada com sucesso!")
            else:
                print("\nFalha ao encerrar a sessão")

if __name__ == "__main__":
    main()
