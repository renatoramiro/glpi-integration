import requests
import os
from dotenv import load_dotenv
import json

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

def get_active_profile(base_url, app_token, session_token):
    """Obtém o perfil ativo do usuário"""
    url = f"{base_url}/getActiveProfile"
    headers = {
        'Content-Type': 'application/json',
        'Session-Token': session_token,
        'App-Token': app_token
    }
    
    response = requests.get(url, headers=headers, verify=False)
    if response.status_code == 200:
        return response.json()['active_profile']
    else:
        raise Exception(f"Falha ao obter perfil ativo: {response.status_code} - {response.text}")

def create_ticket(base_url, app_token, session_token, ticket_data, conversation_history=None):
    """Cria um ticket no GLPI"""
    url = f"{base_url}/Ticket"
    headers = {
        'Content-Type': 'application/json',
        'Session-Token': session_token,
        'App-Token': app_token
    }
    
    # Se houver histórico de conversa, adiciona ao conteúdo do ticket
    if conversation_history and 'content' in ticket_data:
        # Formata o histórico como uma lista HTML
        history_html = "<br><br><strong>Histórico de Conversa:</strong><br><ul>"
        for entry in conversation_history:
            # Verifica se a entrada tem o formato esperado
            if isinstance(entry, dict) and 'speaker' in entry and 'message' in entry:
                history_html += f"<li><strong>{entry['speaker']}:</strong> {entry['message']}</li>"
            else:
                # Se não estiver no formato esperado, adiciona como string
                history_html += f"<li>{entry}</li>"
        history_html += "</ul>"
        
        # Adiciona o histórico ao conteúdo do ticket
        ticket_data['content'] += history_html
    
    payload = {
        'input': ticket_data
    }
    
    response = requests.post(url, headers=headers, json=payload, verify=False)
    if response.status_code in [200, 201]:
        return response.json()
    else:
        raise Exception(f"Falha ao criar ticket: {response.status_code} - {response.text}")

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

def get_ticket(base_url, app_token, session_token, ticket_id):
    """Obtém os detalhes de um ticket específico"""
    url = f"{base_url}/Ticket/{ticket_id}"
    headers = {
        'Content-Type': 'application/json',
        'Session-Token': session_token,
        'App-Token': app_token
    }
    
    response = requests.get(url, headers=headers, verify=False)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Falha ao obter ticket: {response.status_code} - {response.text}")

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
        
        # Obtém o perfil ativo
        profile = get_active_profile(base_url, app_token, session_token)
        print(f"Perfil ativo: {profile['name']}")
        
        # Cria um ticket de exemplo com histórico de conversa
        ticket_data = {
            'name': 'Ticket criado via API REST (1)',
            'content': 'Este é um ticket de teste criado usando requisições REST diretas.',
            'entities_id': 0,  # Entidade raiz
            'externalid': 'CONV-12345',
        }
        
        # Exemplo de histórico de conversa
        conversation_history = [
            {'speaker': 'Cliente', 'message': 'Estou tendo problemas com o acesso ao sistema.'},
            {'speaker': 'Suporte', 'message': 'Posso ajudá-lo com isso. Qual é o erro exato que você está recebendo?'},
            {'speaker': 'Cliente', 'message': 'Recebo uma mensagem de "usuário ou senha inválidos" mesmo usando as credenciais corretas.'},
            {'speaker': 'Suporte', 'message': 'Vou verificar as configurações da sua conta. Pode me informar seu nome de usuário?'},
        ]
        
        result = create_ticket(base_url, app_token, session_token, ticket_data, conversation_history)
        print(f"Ticket criado com sucesso! ID: {result['id']}")
        
        # Obtém e exibe os detalhes do ticket criado
        ticket_details = get_ticket(base_url, app_token, session_token, result['id'])
        print("\nDetalhes do ticket criado:")
        print(f"ID: {ticket_details['id']}")
        print(f"Nome: {ticket_details['name']}")
        print(f"Conteúdo: {ticket_details['content']}")
        
    except Exception as e:
        print(f"Erro: {str(e)}")
    
    finally:
        # Finaliza a sessão se ela foi criada
        if session_token:
            if kill_session(base_url, app_token, session_token):
                print("Sessão encerrada com sucesso!")
            else:
                print("Falha ao encerrar a sessão")

if __name__ == "__main__":
    main()