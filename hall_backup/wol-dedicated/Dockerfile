# Dockerfile pour un micro-service WoL sécurisé
FROM python:3.11-slim

RUN pip install flask

COPY wol_api.py /wol_api.py

CMD ["python", "/wol_api.py"]
