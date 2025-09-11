import os
import sys

# Получение переменных конфигурации
try:
    API_TOKEN = os.environ["API_TOKEN"]
    if not API_TOKEN:
        raise ValueError("API_TOKEN is empty")
    
    ADMIN = int(os.environ["ADMIN_ID"])
    FOR_LOGS = int(os.environ["FOR_LOGS"])
    
    # Уровень логирования (по умолчанию INFO)
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
    
    # Проверяем валидность уровня логирования
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if LOG_LEVEL not in valid_levels:
        print(f"Warning: Invalid LOG_LEVEL '{LOG_LEVEL}', using 'INFO' instead")
        LOG_LEVEL = "INFO"
    
except KeyError as ex:
    print(f"Error: Missing required environment variable: {ex}")
    print("Please ensure the following variables are set: API_TOKEN, ADMIN_ID, FOR_LOGS")
    print("Optional: LOG_LEVEL (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    sys.exit(1)
except ValueError as ex:
    print(f"Error: Invalid value for environment variable: {ex}")
    print("Please check that ADMIN_ID and FOR_LOGS are valid integers and API_TOKEN is not empty")
    sys.exit(1)
except Exception as ex:
    print(f"Unexpected error while reading config: {ex}")
    sys.exit(1)
