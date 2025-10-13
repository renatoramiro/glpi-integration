import asyncio
import json
from ticket_webhook import create_ticket_in_glpi, init_glpi_session, kill_glpi_session

def test_create_ticket_with_user_chat_id():
    """
    Testa a criação de ticket usando apenas o user_chat_id
    """
    print("Iniciando teste de criação de ticket com user_chat_id...")
    
    # Inicializa sessão com o GLPI
    session_token = init_glpi_session()
    if not session_token:
        print("ERRO: Falha ao iniciar sessão com o GLPI")
        return False
    
    try:
        # Simula um histórico de conversa
        conversation_history = [
            {"speaker": "Cliente", "message": "Olá, estou com problemas para acessar o sistema"},
            {"speaker": "Atendente", "message": "Olá! Vou ajudá-lo com isso. Pode me informar qual é o erro exatamente?"},
            {"speaker": "Cliente", "message": "Quando tento fazer login, aparece uma mensagem de erro 500"}
        ]
        
        # Cria o ticket no GLPI
        result = create_ticket_in_glpi(
            title="Problemas de acesso ao sistema - Chat",
            content="Histórico da conversa:\nCliente: Olá, estou com problemas para acessar o sistema\nAtendente: Olá! Vou ajudá-lo com isso. Pode me informar qual é o erro exatamente?\nCliente: Quando tento fazer login, aparece uma mensagem de erro 500",
            external_id="CHAT-TEST-001",
            session_token=session_token,
            entity_id=0,
            conversation_history=conversation_history
        )
        
        if result:
            print(f"SUCESSO: Ticket criado com ID {result.get('id')}")
            return True
        else:
            print("ERRO: Falha ao criar ticket no GLPI")
            return False
            
    finally:
        # Finaliza a sessão com o GLPI
        kill_glpi_session(session_token)

if __name__ == "__main__":
    success = test_create_ticket_with_user_chat_id()
    if success:
        print("\nTeste concluído com sucesso!")
    else:
        print("\nTeste falhou!")
