# MockMentor-AI-Service

A lightweight, rate-limited FastAPI service, containerized for scalable deployment.

---

## 📁 Project Structure

| Path                        | Description                                 |
|-----------------------------|---------------------------------------------|
| `app/main.py`               | FastAPI app entry point                     |
| `app/core/route_limiters.py`| Rate limiting configuration (SlowAPI)       |
| `app/routes/health.py`      | Health check endpoint                       |
| `app/schemas/health_response.py` | Pydantic schema for health endpoint   |
| `requirements.txt`          | Main dependencies                           |
| `requirements-dev.txt`      | Dev dependencies (incl. linter)             |
| `Dockerfile`                | Container build instructions                |
| `.github/workflows/`        | CI/CD pipeline (Docker build & push)        |
| `.gitignore`                | VCS ignore rules                            |

---

## 🚀 Features

- **FastAPI**: Modern, async Python web framework.
- **Rate Limiting**: Per-IP request limits using SlowAPI.
- **Health Endpoint**: `/health` for service status checks.
- **Dockerized**: Production-ready container setup.
- **CI/CD**: Automated Docker build & push via GitHub Actions.

---

## 🏗️ Application Overview

### Main App Initialization (`app/main.py`)

- Initializes FastAPI with metadata.
- Configures global rate limiting.
- Registers the `/health` route.
- Handles rate limit exceptions gracefully.

### Rate Limiting (`app/core/route_limiters.py`)

- Uses SlowAPI's `Limiter`:
  - **Default**: 5 requests/minute per IP.
  - **Custom**: `/health` endpoint allows 10 requests/minute.

### Health Endpoint (`app/routes/health.py`)

- **Route**: `GET /health`
- **Response**: `{ "status": "ok" }`
- **Schema**: Defined in `app/schemas/health_response.py`
- **Rate Limit**: 10 requests/minute per IP

---

## 🗂️ API Endpoints

| Method | Path     | Description         | Rate Limit           | Response Example      |
|--------|----------|---------------------|----------------------|----------------------|
| GET    | `/health`| Health check status | 10 requests/minute/IP| `{ "status": "ok" }` |

---

## 🧩 Dependencies

### Main (`requirements.txt`)

| Package   | Version   | Purpose                |
|-----------|-----------|------------------------|
| fastapi   | 0.104.1   | Web framework          |
| uvicorn   | 0.23.2    | ASGI server            |
| pydantic  | 2.4.2     | Data validation        |
| slowapi   | 0.1.8     | Rate limiting          |

### Development (`requirements-dev.txt`)

| Package   | Version   | Purpose                |
|-----------|-----------|------------------------|
| ruff      | 0.1.3     | Linting                |
| (others)  | -         | Same as main           |

---

## 🐳 Dockerization

### Dockerfile Highlights

- **Base**: `python:3.11-slim`
- **System deps**: Installs `gcc`
- **User**: Runs as non-root `appuser`
- **Workdir**: `/code`
- **Ports**: Exposes `8000`
- **Entrypoint**: Runs with `uvicorn` (4 workers)

```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

## 🔄 CI/CD Pipeline

### GitHub Actions Workflow

| Step                        | Description                                  |
|-----------------------------|----------------------------------------------|
| Checkout code               | Pulls repo code                              |
| Authenticate to GCP         | Uses service account for Docker push         |
| Set up Cloud SDK            | Prepares gcloud CLI                          |
| Configure Docker            | Auths Docker for GCP Artifact Registry       |
| Build Docker image          | Builds image using `Dockerfile`              |
| Push Docker image           | Pushes to GCP Artifact Registry (latest & SHA tags) |

---

## 📝 .gitignore

- Ignores Python cache, virtual environments, test coverage, IDE configs, build artifacts, etc.

---

## 🏁 Quickstart

### Local Development

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### With Docker

```bash
docker build -t mockmentor-ai-service .
docker run -p 8000:8000 mockmentor-ai-service
```

---

## 📞 Health Check Example

```bash
curl http://localhost:8000/health
# Response: { "status": "ok" }
```

---

## 📚 Extending

- Add new routes in `app/routes/`
- Define schemas in `app/schemas/`
- Register routers in `app/main.py`
