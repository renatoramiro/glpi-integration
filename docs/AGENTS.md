# GLPI Ticket Webhook - Agent Guidelines

## Development Commands

### Running the Application
```bash
# Start the webhook server
uvicorn ticket_webhook:app --host 0.0.0.0 --port 8000 --reload

# Run individual test files
python test_webhook.py
python test_glpi_payload.py
```

### Testing
- Test files: `test_webhook.py`, `test_glpi_payload.py`
- Run tests individually with `python <test_file>.py`
- No test framework configured - tests are standalone scripts

## Code Style Guidelines

### Imports
- Standard library imports first, then third-party, then local
- Use `from typing import Optional, Dict, Any` for type hints
- Always import `load_dotenv()` early for environment configuration

### Formatting & Types
- Use type hints for function parameters and return values
- Pydantic models for API payloads with `Optional` fields
- Use f-strings for string formatting
- Maximum line length: ~120 characters

### Naming Conventions
- Functions: `snake_case` with descriptive names
- Variables: `snake_case`, clear and meaningful
- Constants: `UPPER_SNAKE_CASE` for environment variables
- Classes: `PascalCase` for Pydantic models

### Error Handling
- Use try/except blocks for API calls and external dependencies
- Log errors with `logger.error()` including context
- Return `None` for expected failures, raise exceptions for critical errors
- Use HTTPException for FastAPI endpoints with appropriate status codes

### API Patterns
- Initialize GLPI sessions with `init_glpi_session()` and always close with `kill_glpi_session()`
- Use `verify=False` for SSL requests (GLPI often uses self-signed certs)
- Structure webhook handlers to: parse payload → validate → process → respond
- Include comprehensive logging for debugging webhook payloads

### Environment Configuration
- All sensitive data in `.env` file
- Use `os.getenv()` with default values for optional configuration
- Required variables: `GLPI_BASE_URL`, `USER_TOKEN`, `APP_TOKEN`