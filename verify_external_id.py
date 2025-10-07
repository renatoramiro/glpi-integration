#!/usr/bin/env python3
"""
Script para verificar se um ticket tem external_id configurado.
"""

import requests
import os
from dotenv import load_dotenv
import sys

def verify_ticket_external_id(ticket_id):
    """
    Verifica se um ticket tem external_id.
    """
    load_dotenv()
    
    base_url = os.getenv("GLPI_BASE_URL")
    app_token = os.getenv("APP_TOKEN")
    user_token = os.getenv("USER_TOKEN")
    
    print(f"Verificando ticket {ticket_id}...")
    print(f"GLPI URL: {base_url}")
    
    # Inicia sessão
    try:
        response = requests.get(
            f"{base_url}/initSession",
            headers={
                'Authorization': f'user_token {user_token}',
                'App-Token': app_token
            },
            verify=False
        )
        
        if response.status_code != 200:
            print(f"❌ Erro ao iniciar sessão: {response.status_code}")
            print(f"Resposta: {response.text}")
            return
        
        session_token = response.json()['session_token']
        print("✅ Sessão iniciada com sucesso")
        
    except Exception as e:
        print(f"❌ Erro ao conectar ao GLPI: {str(e)}")
        return
    
    # Busca o ticket
    try:
        response = requests.get(
            f"{base_url}/Ticket/{ticket_id}",
            headers={
                'Session-Token': session_token,
                'App-Token': app_token
            },
            verify=False
        )
        
        if response.status_code != 200:
            print(f"❌ Erro ao buscar ticket: {response.status_code}")
            print(f"Resposta: {response.text}")
            return
        
        ticket = response.json()
        
        print("\n" + "="*60)
        print(f"INFORMAÇÕES DO TICKET {ticket_id}")
        print("="*60)
        print(f"Nome: {ticket.get('name')}")
        print(f"Status: {ticket.get('status')}")
        print(f"Data de criação: {ticket.get('date_creation')}")
        print(f"Data de modificação: {ticket.get('date_mod')}")
        
        # Verifica external_id
        external_id = ticket.get('externalid') or ticket.get('external_id')
        
        print("\n" + "="*60)
        print("EXTERNAL ID")
        print("="*60)
        
        if external_id:
            print(f"✅ External ID encontrado: {external_id}")
        else:
            print("❌ External ID NÃO encontrado ou está vazio")
            print("\nPara adicionar external_id ao ticket:")
            print("1. Edite o ticket no GLPI")
            print("2. Preencha o campo 'ID externo'")
            print("3. Salve o ticket")
            print("\nOu use ticket_id em vez de external_id:")
            print(f'  curl -X POST http://localhost:8000/api/add-message \\')
            print(f'    -H "Content-Type: application/json" \\')
            print(f'    -d \'{{')
            print(f'      "ticket_id": {ticket_id},')
            print(f'      "message": "Sua mensagem",')
            print(f'      "user_name": "Seu Nome"')
            print(f'    }}\'')
        
        print("\n" + "="*60)
        
        # Finaliza sessão
        requests.get(
            f"{base_url}/killSession",
            headers={
                'Session-Token': session_token,
                'App-Token': app_token
            },
            verify=False
        )
        
    except Exception as e:
        print(f"❌ Erro ao buscar ticket: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python verify_external_id.py <ticket_id>")
        print("Exemplo: python verify_external_id.py 20")
        sys.exit(1)
    
    ticket_id = int(sys.argv[1])
    verify_ticket_external_id(ticket_id)
