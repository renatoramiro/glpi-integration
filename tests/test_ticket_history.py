#!/usr/bin/env python3
"""
Script de teste para a nova rota de histórico de tickets.

Este script demonstra como usar a API para buscar o histórico completo
de tickets do GLPI com diferentes filtros.
"""

import requests
import json
from datetime import datetime, timedelta

# Configurações
BASE_URL = "http://localhost:8000"

def test_ticket_history_post():
    """Testa a rota POST para buscar histórico de tickets."""
    print("=== Testando rota POST /api/ticket-history ===")
    
    # Exemplo 1: Buscar todos os tickets do último mês
    last_month = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    payload = {
        "start_date": last_month,
        "max_tickets": 10,
        "include_logs": True,
        "include_followups": True,
        "include_solutions": True
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/ticket-history",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Status: {data.get('status')}")
            print(f"Message: {data.get('message')}")
            
            summary = data.get('summary', {})
            print(f"\n=== Resumo ===")
            print(f"Total de tickets: {summary.get('total_tickets', 0)}")
            print(f"Total de logs: {summary.get('total_logs', 0)}")
            print(f"Total de followups: {summary.get('total_followups', 0)}")
            print(f"Total de soluções: {summary.get('total_solutions', 0)}")
            
            tickets = data.get('tickets', [])
            print(f"\n=== Primeiros 3 tickets ===")
            for i, ticket in enumerate(tickets[:3]):
                print(f"\nTicket {i+1}:")
                print(f"  ID: {ticket.get('id')}")
                details = ticket.get('details', {})
                print(f"  Título: {details.get('name', 'N/A')}")
                print(f"  Status: {details.get('status', 'N/A')}")
                print(f"  Data criação: {details.get('date_creation', 'N/A')}")
                print(f"  Logs: {len(ticket.get('logs', []))}")
                print(f"  Followups: {len(ticket.get('followups', []))}")
                print(f"  Soluções: {len(ticket.get('solutions', []))}")
        else:
            print(f"Erro: {response.text}")
            
    except Exception as e:
        print(f"Erro na requisição: {str(e)}")

def test_ticket_history_get():
    """Testa a rota GET para buscar histórico de tickets."""
    print("\n=== Testando rota GET /api/ticket-history ===")
    
    # Exemplo 2: Buscar tickets solucionados (status 5)
    params = {
        "status_filter": 5,
        "max_tickets": 5,
        "include_logs": False,  # Apenas para testar
        "include_followups": True,
        "include_solutions": True
    }
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/ticket-history",
            params=params
        )
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Status: {data.get('status')}")
            print(f"Message: {data.get('message')}")
            
            summary = data.get('summary', {})
            print(f"\n=== Resumo ===")
            print(f"Total de tickets: {summary.get('total_tickets', 0)}")
            print(f"Total de logs: {summary.get('total_logs', 0)}")
            print(f"Total de followups: {summary.get('total_followups', 0)}")
            print(f"Total de soluções: {summary.get('total_solutions', 0)}")
            
            filters = summary.get('filters_applied', {})
            print(f"\n=== Filtros aplicados ===")
            for key, value in filters.items():
                print(f"  {key}: {value}")
                
        else:
            print(f"Erro: {response.text}")
            
    except Exception as e:
        print(f"Erro na requisição: {str(e)}")

def test_ticket_history_by_date_range():
    """Testa busca por intervalo de datas."""
    print("\n=== Testando busca por intervalo de datas ===")
    
    # Últimos 7 dias
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    payload = {
        "start_date": start_date,
        "end_date": end_date,
        "max_tickets": 20,
        "include_logs": True,
        "include_followups": True,
        "include_solutions": True
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/ticket-history",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            summary = data.get('summary', {})
            print(f"Tickets de {start_date} a {end_date}: {summary.get('total_tickets', 0)}")
            
            # Mostra detalhes dos logs se houver
            tickets = data.get('tickets', [])
            total_logs = 0
            for ticket in tickets:
                logs = ticket.get('logs', [])
                if logs:
                    print(f"\nLogs do ticket {ticket.get('id')}:")
                    for log in logs[:3]:  # Primeiros 3 logs
                        print(f"  - {log.get('date_mod', 'N/A')}: {log.get('user_name', 'N/A')} - {log.get('new_value', 'N/A')}")
                    total_logs += len(logs)
            
            print(f"\nTotal de logs no período: {total_logs}")
        else:
            print(f"Erro: {response.text}")
            
    except Exception as e:
        print(f"Erro na requisição: {str(e)}")

def test_health_check():
    """Verifica se o serviço está ativo."""
    print("=== Verificando saúde do serviço ===")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"Status: {data.get('status')}")
            print(f"Service: {data.get('service')}")
            return True
        else:
            print(f"Serviço não está saudável: {response.status_code}")
            return False
    except Exception as e:
        print(f"Erro ao verificar saúde: {str(e)}")
        return False

if __name__ == "__main__":
    print("Iniciando testes da API de histórico de tickets...")
    
    # Verifica se o serviço está ativo
    if not test_health_check():
        print("\n❌ Serviço não está disponível. Verifique se o servidor está rodando.")
        exit(1)
    
    print("\n✅ Serviço está ativo!")
    
    # Executa os testes
    test_ticket_history_post()
    test_ticket_history_get()
    test_ticket_history_by_date_range()
    
    print("\n=== Testes concluídos ===")
    print("\nExemplos de uso:")
    print("1. Buscar todos os tickets:")
    print('   curl -X POST http://localhost:8000/api/ticket-history -H "Content-Type: application/json" -d \'{"max_tickets": 10}\'')
    print("\n2. Buscar tickets por data:")
    print('   curl -X POST http://localhost:8000/api/ticket-history -H "Content-Type: application/json" -d \'{"start_date": "2025-01-01", "max_tickets": 10}\'')
    print("\n3. Buscar tickets solucionados:")
    print('   curl -X GET "http://localhost:8000/api/ticket-history?status_filter=5&max_tickets=10"')
    print("\n4. Buscar sem logs (mais rápido):")
    print('   curl -X POST http://localhost:8000/api/ticket-history -H "Content-Type: application/json" -d \'{"include_logs": false, "max_tickets": 10}\'')