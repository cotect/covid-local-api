FROM tiangolo/uvicorn-gunicorn-fastapi:python3.7

COPY ./app/ /app

RUN pip install -e /app

# Default Configuration
ENV MODULE_NAME="covid_local_api.endpoints"