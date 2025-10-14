#!/usr/bin/env python3
"""
Script para testar diferentes formatos de payload que o GLPI pode enviar.
"""

import requests
import json
from datetime import datetime

def test_payload_format_1():
    """
    Testa o formato de payload mais completo.
    """
    url = "http://localhost:8000/webhook/ticket-closed"
    
    payload = {
        "ticket_id": 123,
        "ticket_name": "Problema com acesso ao sistema",
        "closed_by": "Suporte Técnico",
        "closed_at": datetime.now().isoformat() + "Z",
        "solution": "Reset de senha realizado com sucesso.",
        "requester_email": "cliente@empresa.com",
        "requester_name": "Cliente Exemplo",
        "additional_data": {
            "status": "Fechado",
            "priority": "Alta",
            "category": "Acesso"
        }
    }
    
    print("Testando formato 1 (completo):")
    print(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Erro: {str(e)}")
    
    print("\n" + "="*50 + "\n")

def test_payload_format_2():
    """
    Testa o formato de payload que o GLPI pode enviar diretamente.
    """
    url = "http://localhost:8000/webhook/ticket-closed"
    
    payload = {
        "id": 124,
        "name": "Erro na impressora",
        "content": "Impressora não está respondendo",
        "status": 6,  # Fechado
        "users_id_lastupdater": 5,
        "date_mod": datetime.now().isoformat(),
        "solution": "Reinicialização da impressora resolveu o problema",
        "_users_id_requester": 10
    }
    
    print("Testando formato 2 (GLPI direto):")
    print(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Erro: {str(e)}")
    
    print("\n" + "="*50 + "\n")

def test_payload_format_3():
    """
    Testa um formato mínimo de payload.
    """
    url = "http://localhost:8000/webhook/ticket-closed"
    
    payload = {
        "ticket_id": 125
    }
    
    print("Testando formato 3 (mínimo):")
    print(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Erro: {str(e)}")
    
    print("\n" + "="*50 + "\n")

def main():
    print("Testando diferentes formatos de payload para o webhook do GLPI\n")
    
    test_payload_format_1()
    test_payload_format_2()
    test_payload_format_3()

if __name__ == "__main__":
    main()
