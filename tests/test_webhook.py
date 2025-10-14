#!/usr/bin/env python3
"""
Script para testar o webhook de tickets fechados.
"""

import requests
import json
from datetime import datetime

def test_ticket_closed_webhook():
    """
    Testa o endpoint de ticket fechado.
    """
    url = "http://localhost:8000/webhook/ticket-closed"
    
    payload = {
        "ticket_id": 123,
        "ticket_name": "Problema com acesso ao sistema",
        "closed_by": "Suporte Técnico",
        "closed_at": datetime.now().isoformat() + "Z",
        "solution": "Reset de senha realizado com sucesso. As credenciais foram atualizadas e o usuário pode acessar o sistema normalmente.",
        "requester_email": "cliente@empresa.com",
        "requester_name": "Cliente Exemplo",
        "additional_data": {
            "priority": "alta",
            "category": "Acesso",
            "resolution_time": "2 horas"
        }
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Erro ao testar webhook: {str(e)}")

def test_health_check():
    """
    Testa o endpoint de health check.
    """
    url = "http://localhost:8000/health"
    
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Erro ao testar health check: {str(e)}")

if __name__ == "__main__":
    print("Testando health check...")
    test_health_check()
    
    print("\nTestando webhook de ticket fechado...")
    test_ticket_closed_webhook()
