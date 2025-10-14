# Testes da API GLPI Ticket Webhook

## Como executar os testes

### Instalar dependências de desenvolvimento
```bash
pip install -r requirements-dev.txt
```

### Executar todos os testes
```bash
python -m pytest tests/ -v
```

### Executar um teste específico
```bash
python -m pytest tests/test_ticket_webhook.py::TestHealthCheck::test_health_check -v
```

### Executar testes com coverage
```bash
python -m pytest tests/ --cov=. --cov-report=html
```

## Estrutura dos testes

- `test_ticket_webhook.py`: Testes principais da API
- `conftest.py`: Fixtures e configurações compartilhadas

## O que é testado

1. **Health Check**: Verifica se o serviço está ativo
2. **Criação de Tickets**: Testa criação com e sem user_chat_id
3. **Webhook de Ticket Fechado**: Testa processamento de tickets fechados
4. **Webhook de Followup**: Testa recebimento de novas respostas
5. **Adicionar Mensagem**: Testa adição de mensagens a tickets existentes
6. **Debug Webhook**: Testa endpoint de debug
7. **Modelos Pydantic**: Testa validação dos modelos de dados