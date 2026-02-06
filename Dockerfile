FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY apps/cabinet/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY apps/cabinet/ .

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
