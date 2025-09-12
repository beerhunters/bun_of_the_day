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
    
    # Дополнительные настройки логирования
    LOG_TO_FILE = os.environ.get("LOG_TO_FILE", "true").lower() in ["true", "1", "yes"]
    LOG_TO_TELEGRAM = os.environ.get("LOG_TO_TELEGRAM", "true").lower() in ["true", "1", "yes"]  
    LOG_FILE_LEVEL = os.environ.get("LOG_FILE_LEVEL", "ERROR").upper()
    LOG_TELEGRAM_LEVEL = os.environ.get("LOG_TELEGRAM_LEVEL", "ERROR").upper()
    
    # Настройки для rate limiting и retry
    REQUEST_DELAY = float(os.environ.get("REQUEST_DELAY", "0.1"))  # Задержка между запросами в секундах
    MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "3"))  # Максимальное количество попыток
    RETRY_DELAY = int(os.environ.get("RETRY_DELAY", "5"))  # Базовая задержка для повторных попыток
    
    # Проверяем валидность уровней для файла и телеграма
    if LOG_FILE_LEVEL not in valid_levels:
        print(f"Warning: Invalid LOG_FILE_LEVEL '{LOG_FILE_LEVEL}', using 'ERROR' instead")
        LOG_FILE_LEVEL = "ERROR"
        
    if LOG_TELEGRAM_LEVEL not in valid_levels:
        print(f"Warning: Invalid LOG_TELEGRAM_LEVEL '{LOG_TELEGRAM_LEVEL}', using 'ERROR' instead") 
        LOG_TELEGRAM_LEVEL = "ERROR"
    
except KeyError as ex:
    print(f"Error: Missing required environment variable: {ex}")
    print("Please ensure the following variables are set: API_TOKEN, ADMIN_ID, FOR_LOGS")
    print("Optional logging variables:")
    print("  LOG_LEVEL (DEBUG, INFO, WARNING, ERROR, CRITICAL) - Console output level")
    print("  LOG_TO_FILE (true/false) - Enable file logging")
    print("  LOG_TO_TELEGRAM (true/false) - Enable Telegram error notifications")
    print("  LOG_FILE_LEVEL (DEBUG, INFO, WARNING, ERROR, CRITICAL) - File logging level")
    print("  LOG_TELEGRAM_LEVEL (DEBUG, INFO, WARNING, ERROR, CRITICAL) - Telegram notifications level")
    sys.exit(1)
except ValueError as ex:
    print(f"Error: Invalid value for environment variable: {ex}")
    print("Please check that ADMIN_ID and FOR_LOGS are valid integers and API_TOKEN is not empty")
    sys.exit(1)
except Exception as ex:
    print(f"Unexpected error while reading config: {ex}")
    sys.exit(1)
