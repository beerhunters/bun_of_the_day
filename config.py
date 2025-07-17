import os

# Получение переменных конфигурации
try:
    API_TOKEN = os.environ["API_TOKEN"]
    ADMIN = int(os.environ["ADMIN_ID"])
    FOR_LOGS = int(os.environ["FOR_LOGS"])
except (TypeError, ValueError) as ex:
    print("Error while reading config:", ex)
