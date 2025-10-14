import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime

from ticket_webhook import app, TicketClosedPayload, CreateTicketPayload

client = TestClient(app)

class TestHealthCheck:
    def test_health_check(self):
        """Testa o endpoint de health check"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy", "service": "GLPI Ticket Webhook"}

class TestCreateTicket:
    @patch('ticket_webhook.init_glpi_session')
    @patch('ticket_webhook.kill_glpi_session')
    @patch('ticket_webhook.create_ticket_in_glpi')
    @patch('ticket_webhook.load_chat_data')
    @patch('ticket_webhook.supabase')
    def test_create_ticket_success_with_chat_id(self, mock_supabase, mock_load_chat, mock_create, mock_kill, mock_init):
        """Testa criação de ticket com user_chat_id"""
        # Setup mocks
        mock_init.return_value = "session_token"
        mock_load_chat.return_value = {
            'title': 'Test Ticket Title',
            'conversation_history': [{'msg': 'test'}]
        }
        mock_create.return_value = {'id': 123}
        mock_supabase.return_value = True
        
        payload = {
            "user_chat_id": "chat-12345",
            "entity_id": 1
        }
        
        response = client.post("/api/create-ticket", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["ticket_id"] == 123
        assert data["user_chat_id"] == "chat-12345"
        
        mock_init.assert_called_once()
        mock_create.assert_called_once()
        mock_kill.assert_called_once()

    @patch('ticket_webhook.init_glpi_session')
    @patch('ticket_webhook.kill_glpi_session')
    @patch('ticket_webhook.create_ticket_in_glpi')
    def test_create_ticket_without_chat_id(self, mock_create, mock_kill, mock_init):
        """Testa criação de ticket sem user_chat_id (usa título padrão)"""
        mock_init.return_value = "session_token"
        mock_create.return_value = {'id': 456}
        
        payload = {"entity_id": 1, "external_id": "test-external-id"}
        
        response = client.post("/api/create-ticket", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["ticket_id"] == 456

    @patch('ticket_webhook.supabase', None)
    def test_create_ticket_supabase_not_configured(self):
        """Testa erro quando Supabase não está configurado"""
        payload = {"user_chat_id": "chat-12345"}
        
        response = client.post("/api/create-ticket", json=payload)
        
        assert response.status_code == 500
        assert "Serviço Supabase não configurado" in response.json()["detail"]

class TestTicketClosedWebhook:
    @patch('ticket_webhook.init_glpi_session')
    @patch('ticket_webhook.kill_glpi_session')
    @patch('ticket_webhook.get_ticket_details')
    @patch('ticket_webhook.get_user_details')
    @patch('ticket_webhook.get_ticket_followups')
    @patch('ticket_webhook.get_ticket_solution')
    @patch('ticket_webhook.process_closed_ticket')
    def test_ticket_closed_success(self, mock_process, mock_solution, mock_followups, 
                                  mock_user, mock_details, mock_kill, mock_init):
        """Testa webhook de ticket fechado com sucesso"""
        mock_init.return_value = "session_token"
        mock_details.return_value = {
            'name': 'Test Ticket',
            'users_id_lastupdater': 1,
            '_users_id_requester': 2,
            'date_mod': '2023-01-01 10:00:00'
        }
        mock_user.side_effect = [
            {'firstname': 'John', 'realname': 'Doe', 'name': 'johndoe'},
            {'firstname': 'Jane', 'realname': 'Smith', 'email': 'jane@example.com', 'name': 'janesmith'}
        ]
        mock_followups.return_value = [{'content': 'Test followup'}]
        mock_solution.return_value = [{'content': 'Test solution'}]
        
        payload = {
            "item": {
                "id": 123,
                "name": "Test Ticket",
                "status": {"id": 6},  # Status 6 = Fechado
                "users_id_lastupdater": 1,
                "date_mod": "2023-01-01 10:00:00"
            }
        }
        
        response = client.post("/webhook/ticket-closed", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["ticket_id"] == 123
        
        mock_process.assert_called_once()

    def test_ticket_not_closed_ignored(self):
        """Testa que tickets não fechados são ignorados"""
        payload = {
            "item": {
                "id": 123,
                "status": {"id": 5}  # Status 5 != Fechado
            }
        }
        
        response = client.post("/webhook/ticket-closed", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"
        assert "não está fechado" in data["message"]

    @patch('ticket_webhook.init_glpi_session')
    def test_ticket_closed_glpi_connection_error(self, mock_init):
        """Testa erro de conexão com GLPI"""
        mock_init.return_value = None
        
        payload = {
            "item": {
                "id": 123,
                "status": {"id": 6}
            }
        }
        
        response = client.post("/webhook/ticket-closed", json=payload)
        
        assert response.status_code == 500
        assert "Erro ao processar ticket" in response.json()["detail"]

class TestFollowupWebhook:
    @patch('ticket_webhook.init_glpi_session')
    @patch('ticket_webhook.kill_glpi_session')
    @patch('ticket_webhook.get_ticket_details')
    @patch('ticket_webhook.get_user_details')
    @patch('ticket_webhook.send_response_to_platform')
    def test_followup_added_success(self, mock_send, mock_user, mock_details, mock_kill, mock_init):
        """Testa webhook de followup adicionado com sucesso"""
        mock_init.return_value = "session_token"
        mock_details.return_value = {
            'externalid': 'EXT-123',
            'name': 'Test Ticket'
        }
        mock_user.return_value = {
            'firstname': 'John',
            'realname': 'Doe',
            'name': 'johndoe'
        }
        
        payload = {
            "item": {
                "id": 456,
                "items_id": 123,
                "content": "Test followup content",
                "users_id": 1,
                "date_creation": "2023-01-01 10:00:00",
                "is_private": 0
            }
        }
        
        response = client.post("/webhook/followup-added", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["ticket_id"] == 123
        assert data["external_id"] == "EXT-123"
        
        mock_send.assert_called_once()

class TestAddMessage:
    @patch('ticket_webhook.init_glpi_session')
    @patch('ticket_webhook.kill_glpi_session')
    @patch('ticket_webhook.search_ticket_by_external_id')
    @patch('ticket_webhook.add_followup_to_ticket')
    def test_add_message_by_external_id(self, mock_add, mock_search, mock_kill, mock_init):
        """Testa adicionar mensagem usando external_id"""
        mock_init.return_value = "session_token"
        mock_search.return_value = 123
        mock_add.return_value = {'id': 789}
        
        payload = {
            "external_id": "EXT-123",
            "message": "Test message",
            "user_name": "Test User"
        }
        
        response = client.post("/api/add-message", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["ticket_id"] == 123
        assert data["external_id"] == "EXT-123"
        assert data["followup_id"] == 789

    @patch('ticket_webhook.init_glpi_session')
    @patch('ticket_webhook.kill_glpi_session')
    @patch('ticket_webhook.search_ticket_by_id')
    @patch('ticket_webhook.add_followup_to_ticket')
    def test_add_message_by_ticket_id(self, mock_add, mock_search, mock_kill, mock_init):
        """Testa adicionar mensagem usando ticket_id"""
        mock_init.return_value = "session_token"
        mock_search.return_value = {
            'id': 123,
            'externalid': 'EXT-456'
        }
        mock_add.return_value = {'id': 790}
        
        payload = {
            "ticket_id": 123,
            "message": "Test message",
            "user_name": "Test User"
        }
        
        response = client.post("/api/add-message", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["ticket_id"] == 123
        assert data["external_id"] == "EXT-456"

    def test_add_message_missing_identifiers(self):
        """Testa erro quando não fornece external_id nem ticket_id"""
        payload = {
            "message": "Test message"
        }
        
        response = client.post("/api/add-message", json=payload)
        
        assert response.status_code == 400
        assert "external_id ou ticket_id é obrigatório" in response.json()["detail"]

    def test_add_message_missing_message(self):
        """Testa erro quando não fornece mensagem"""
        payload = {
            "external_id": "EXT-123"
        }
        
        response = client.post("/api/add-message", json=payload)
        
        assert response.status_code == 400
        assert "message é obrigatório" in response.json()["detail"]

class TestDebugWebhook:
    def test_debug_webhook(self):
        """Testa endpoint de debug"""
        payload = {"test": "data"}
        
        response = client.post("/webhook/debug", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "debugged"
        assert "json_payload" in data
        assert "headers" in data
        assert data["json_payload"] == payload

class TestPydanticModels:
    def test_ticket_closed_payload(self):
        """Testa modelo TicketClosedPayload"""
        data = {
            "ticket_id": 123,
            "ticket_name": "Test Ticket",
            "closed_by": "John Doe",
            "closed_at": "2023-01-01 10:00:00",
            "solution": "Test solution"
        }
        
        payload = TicketClosedPayload(**data)
        assert payload.ticket_id == 123
        assert payload.ticket_name == "Test Ticket"
        assert payload.closed_by == "John Doe"

    def test_create_ticket_payload(self):
        """Testa modelo CreateTicketPayload"""
        data = {
            "external_id": "EXT-123",
            "title": "Test Ticket",
            "entity_id": 1,
            "user_chat_id": "chat-123"
        }
        
        payload = CreateTicketPayload(**data)
        assert payload.external_id == "EXT-123"
        assert payload.title == "Test Ticket"
        assert payload.entity_id == 1
        assert payload.user_chat_id == "chat-123"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])