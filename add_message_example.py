#!/usr/bin/env python3
"""
Exemplo de como adicionar mensagens da plataforma ao ticket do GLPI.
"""

import requests
import json

def add_message_to_glpi_ticket(external_id, message, user_name="Usuário"):
    """
    Adiciona uma mensagem ao ticket do GLPI usando o external_id.
    
    Args:
        external_id: ID externo do ticket (ID da conversa na plataforma)
        message: Mensagem do usuário
        user_name: Nome do usuário (opcional)
    
    Returns:
        Resposta da API
    """
    # URL do webhook
    webhook_url = "http://localhost:8000/api/add-message"
    
    # Payload
    payload = {
        "external_id": external_id,
        "message": message,
        "user_name": user_name
    }
    
    print(f"Enviando mensagem para o ticket com external_id: {external_id}")
    print(f"Mensagem: {message}")
    print(f"Usuário: {user_name}")
    
    try:
        response = requests.post(webhook_url, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ Mensagem adicionada com sucesso!")
            print(f"Ticket ID: {result.get('ticket_id')}")
            print(f"Followup ID: {result.get('followup_id')}")
            return result
        else:
            print(f"\n❌ Erro ao adicionar mensagem: {response.status_code}")
            print(f"Detalhes: {response.text}")
            return None
            
    except Exception as e:
        print(f"\n❌ Erro: {str(e)}")
        return None

def main():
    print("=" * 60)
    print("Exemplo de adição de mensagens ao ticket do GLPI")
    print("=" * 60)
    
    # Exemplo 1: Primeira mensagem do usuário (cria o ticket)
    print("\n1. Simulando criação de ticket...")
    external_id = "CONV-1133"
    
    # Aqui você criaria o ticket no GLPI com external_id
    # (usando o código de create_ticket_with_external_id.py)
    print(f"Ticket criado com external_id: {external_id}")
    
    # Exemplo 2: Usuário envia segunda mensagem
    print("\n2. Usuário envia segunda mensagem...")
    add_message_to_glpi_ticket(
        external_id=external_id,
        message="Ainda estou com o problema. Pode me ajudar?",
        user_name="João Silva"
    )
    
    # Exemplo 3: Usuário envia terceira mensagem
    print("\n3. Usuário envia terceira mensagem...")
    add_message_to_glpi_ticket(
        external_id=external_id,
        message="Tentei reiniciar mas não funcionou.",
        user_name="João Silva"
    )
    
    # Exemplo 4: Usuário envia mensagem com informações adicionais
    print("\n4. Usuário envia informações adicionais...")
    add_message_to_glpi_ticket(
        external_id=external_id,
        message="O erro que aparece é: 'Conexão recusada'. Isso acontece desde ontem.",
        user_name="João Silva"
    )

if __name__ == "__main__":
    main()
