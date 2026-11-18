FROM python:3.13.18-slim-trixie

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY transfer_app.py transfer-form.html ./

# The service runs unprivileged, and listens on every interface so that the port mapping
# of compose.yaml reaches it.
USER nobody
ENV HOST=0.0.0.0 PORT=8000
EXPOSE 8000
CMD ["python", "transfer_app.py"]
