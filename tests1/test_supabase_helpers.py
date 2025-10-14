import os
from supabase_helpers import load_chat_data, supabase

def test_supabase_initialization():
    """
    Testa se o cliente Supabase foi inicializado corretamente
    """
    print("Testando inicialização do Supabase...")
    
    if supabase:
        print("✓ Cliente Supabase inicializado com sucesso")
    else:
        print("✗ Cliente Supabase não foi inicializado")
        print("Verifique se as variáveis de ambiente SUPABASE_URL e SUPABASE_KEY estão configuradas")
    
    return supabase is not None

def test_load_chat_data():
    """
    Testa a função load_chat_data com um ID de chat de exemplo
    """
    print("\nTestando load_chat_data...")
    
    # Usa um ID de chat de exemplo (não esperamos que ele exista)
    test_chat_id = "test-chat-id-123"
    
    try:
        result = load_chat_data(test_chat_id)
        print(f"✓ Função load_chat_data executada sem erros")
        print(f"  Resultado: title={result.get('title')}, conversation_history={len(result.get('conversation_history', []))} mensagens")
        return True
    except Exception as e:
        print(f"✗ Erro ao executar load_chat_data: {str(e)}")
        return False

if __name__ == "__main__":
    print("=== Teste dos Helpers do Supabase ===")
    
    # Testa a inicialização
    supabase_ok = test_supabase_initialization()
    
    # Testa a função de carregar dados do chat
    if supabase_ok:
        load_ok = test_load_chat_data()
        
        if load_ok:
            print("\n✓ Todos os testes passaram!")
        else:
            print("\n✗ Alguns testes falharam")
    else:
        print("\n⚠ Não foi possível testar load_chat_data porque o Supabase não está configurado")
