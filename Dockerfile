# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system deps (optional, for chroma /uvicorn etc.)
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

COPY requirement.txt /app/
RUN pip install --no-cache-dir -r requirement.txt

COPY . /app

# Set env var for Streamlit in container
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_PORT=8501
# Expect OPENAI_API_KEY passed at runtime

EXPOSE 8501

# Default command to run the Streamlit app
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]