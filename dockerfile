# Используем лёгкий Python 3.12 (slim — без лишнего)
FROM python:3.12-slim-bookworm

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем и устанавливаем зависимости (только aiogram)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код
COPY . .

# Запускаем именно твой скрипт (не gunicorn!)
CMD ["python", "LeadBot.py"]