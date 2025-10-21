import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase_helpers import save_message_to_chat

@patch('supabase_helpers.supabase')
def test_save_message_to_chat_success(mock_supabase):
    """Testa o salvamento de mensagem com sucesso"""
    # Setup mock
    mock_result = Mock()
    mock_result.data = [{'id': 1}]
    mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_result
    
    # Testa a função
    result = save_message_to_chat("chat-123", "Test message", "GLPI")
    
    # Verificações
    assert result == True
    mock_supabase.table.assert_called_once_with("messages")
    mock_supabase.table.return_value.insert.assert_called_once()
    mock_supabase.table.return_value.insert.return_value.execute.assert_called_once()

@patch('supabase_helpers.supabase')
def test_save_message_to_chat_failure(mock_supabase):
    """Testa o salvamento de mensagem quando falha"""
    # Setup mock
    mock_result = Mock()
    mock_result.data = None
    mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_result
    
    # Testa a função
    result = save_message_to_chat("chat-123", "Test message", "GLPI")
    
    # Verificações
    assert result == False

@patch('supabase_helpers.supabase', None)
def test_save_message_to_chat_no_supabase():
    """Testa o salvamento de mensagem quando Supabase não está configurado"""
    # Testa a função
    result = save_message_to_chat("chat-123", "Test message", "GLPI")
    
    # Verificações
    assert result == False

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
