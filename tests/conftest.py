import pytest
import sys
import os

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture
def sample_ticket_payload():
    """Payload de exemplo para ticket fechado"""
    return {
        "item": {
            "id": 123,
            "name": "Test Ticket",
            "status": {"id": 6},
            "users_id_lastupdater": 1,
            "date_mod": "2023-01-01 10:00:00"
        }
    }

@pytest.fixture
def sample_followup_payload():
    """Payload de exemplo para followup"""
    return {
        "item": {
            "id": 456,
            "items_id": 123,
            "content": "Test followup content",
            "users_id": 1,
            "date_creation": "2023-01-01 10:00:00",
            "is_private": 0
        }
    }

@pytest.fixture
def sample_create_ticket_payload():
    """Payload de exemplo para criação de ticket"""
    return {
        "user_chat_id": "chat-12345",
        "entity_id": 1
    }