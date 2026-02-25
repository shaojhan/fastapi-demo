# FastAPI Demo

A production-ready FastAPI application following **Domain-Driven Design (DDD)** principles with a clean architecture, comprehensive testing, and enterprise-grade features.

## Features

- **Domain-Driven Design**: Clean separation between domain logic, infrastructure, and application layers
- **Repository Pattern**: Abstract data access with domain model mapping
- **Unit of Work Pattern**: Transaction management and atomic operations
- **JWT Authentication**: Secure user authentication with JWT tokens
- **Google OAuth2 / SSO**: Third-party login with Google OAuth2 and enterprise SSO (OIDC / SAML)
- **Email Verification**: Registration email verification and password reset flows
- **Messaging System**: Internal user-to-user messaging with threads and read tracking
- **Schedule Management**: CRUD schedules with Google Calendar sync
- **AI Scheduling Assistant**: Natural language scheduling via Ollama (self-hosted LLM) with multi-round conversation, smart conflict detection, and available slot suggestion
- **HR Approval AI**: Manager-facing conversational interface to review, summarize, approve, or reject employee leave/expense requests via natural language
- **MQTT Notification Summary**: Daily AI-generated email digest of recent MQTT events; supports manual admin trigger and Celery beat auto-schedule
- **MQTT Integration**: Publish/subscribe messaging with Mosquitto broker, message persistence
- **Kafka Integration**: Distributed streaming with Apache Kafka (KRaft mode), async producer/consumer, message persistence
- **Async Task Processing**: Celery + Redis for background job execution with progress tracking
- **Object Storage**: S3-compatible avatar storage via MinIO
- **Database Migrations**: Alembic for version-controlled schema changes
- **Comprehensive Testing**: 931 tests · 81% coverage (unit + integration)
- **API Documentation**: Auto-generated Swagger UI and ReDoc
- **Structured Logging**: Request tracing with loguru

## Prerequisites

- Python 3.12+
- Poetry (dependency management)
- MySQL / MariaDB
- Redis (for Celery broker and result backend)
- Docker / Podman (for MinIO, Mosquitto, etc.)
- Ollama (optional, for AI scheduling assistant)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/shaojhan/fastapi-demo.git
cd fastapi-demo
```

### 2. Install dependencies

```bash
poetry install
```

### 3. Configure environment

Copy the template and fill in your values:

```bash
cp template/dev.env .env
```

Key environment variables:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | MySQL connection string |
| `JWT_KEY` | Secret key for JWT signing |
| `BROKER_URL` | Redis URL for Celery broker |
| `CELERY_RESULT_BACKEND` | Redis URL for Celery results |
| `S3_ENDPOINT_URL` | MinIO / S3 endpoint |
| `MQTT_BROKER_HOST` | Mosquitto broker host |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka broker address (default: `localhost:9092`) |
| `GOOGLE_CLIENT_ID` | Google OAuth2 client ID |
| `MAIL_SERVER` | SMTP server for email |
| `OLLAMA_BASE_URL` | Ollama server URL (default: `http://localhost:11434`) |
| `OLLAMA_MODEL` | LLM model name (default: `qwen3:8b`) |
| `MQTT_SUMMARY_HOURS` | Look-back window for daily MQTT digest (default: `24`) |

### 4. Start infrastructure services

```bash
./scripts/redis.sh start       # Redis      localhost:6379
./scripts/minio.sh start       # MinIO      localhost:9000 (Console: 9001)
./scripts/mosquitto.sh start   # Mosquitto  localhost:1883
./scripts/kafka.sh start       # Kafka      localhost:9092
```

All scripts support: `start` / `stop` / `restart` / `logs`

Or use Docker Compose:

```bash
docker compose up -d
```

### 5. Initialize database

```bash
poetry run db-head
```

## Running the Application

### Development Server

```bash
poetry run dev
```

The API will be available at:
- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`

### Celery Worker

```bash
poetry run celery
```

### Celery Beat (Periodic Tasks)

```bash
celery -A app.tasks beat --loglevel=info
```

Registered schedules:

| Task | Schedule | Description |
|------|----------|-------------|
| `mqtt.summary.daily_digest` | Every day at 08:00 (Asia/Taipei) | Generate AI summary of MQTT messages and email all verified users |

### Nginx (Optional)

```bash
poetry run nginx
```

## Testing

```bash
# Run all tests (unit + integration)
poetry run test

# Run specific test suites
pytest tests/unit/domain/ -v
pytest tests/unit/repo/ -v
pytest tests/unit/service/ -v
pytest tests/integration/ -v

# Full coverage report
pytest tests/ --cov=app --cov-report=term-missing
```

### Test Structure

| Suite | Path | Focus |
|-------|------|-------|
| Unit — Domain | `tests/unit/domain/` | Domain model logic, value objects, invariants |
| Unit — Repository | `tests/unit/repo/` | Repository CRUD, query methods |
| Unit — Service | `tests/unit/service/` | Service orchestration with mocked dependencies |
| Unit — UoW | `tests/unit/unitofwork/` | Unit of Work commit / rollback |
| Integration | `tests/integration/` | Full HTTP → Router → Service → Repository → SQLite stack |

### Coverage Report

> 931 tests · **81% overall** (`pytest tests/ --cov=app`)

#### Domain Layer

| Module | Coverage |
|--------|----------|
| `domain/EmployeeCsvImportModel` | 100% |
| `domain/LoginRecordModel` | 100% |
| `domain/MQTTModel` | 100% |
| `domain/services/AuthenticationService` | 100% |
| `domain/MessageModel` | 99% |
| `domain/ChatModel` | 98% |
| `domain/EmployeeModel` | 98% |
| `domain/ScheduleModel` | 98% |
| `domain/SSOModel` | 98% |
| `domain/KafkaModel` | 97% |
| `domain/ApprovalModel` | 95% |
| `domain/AuthorityModel` | 95% |
| `domain/UserModel` | 94% |

#### Repository Layer

| Module | Coverage |
|--------|----------|
| `repositories/BaseRepository` | 100% |
| `repositories/ChatRepository` | 100% |
| `repositories/KafkaRepository` | 100% |
| `repositories/LoginRecordRepository` | 100% |
| `repositories/MQTTRepository` | 100% |
| `repositories/ScheduleRepository` | 100% |
| `repositories/WorkflowRepository` | 100% |
| `repositories/SSORepository` | 99% |
| `repositories/UserRepository` | 99% |
| `repositories/EmployeeRepository` | 99% |
| `repositories/ApprovalRepository` | 97% |
| `repositories/MessageRepository` | 91% |

#### Service Layer (Application Services)

| Module | Coverage |
|--------|----------|
| `services/LoginRecordService` | 100% |
| `services/MessageService` | 100% |
| `services/MQTTService` | 100% |
| `services/SSOAdminService` | 95% |
| `services/FileReadService` | 91% |
| `services/ApprovalService` | 90% |
| `services/AuthService` | 88% |
| `services/GitHubOAuthService` | 86% |
| `services/KafkaService` | 84% |
| `services/ScheduleAgentService` | 75% |
| `services/ApprovalAgentService` | 75% |
| `services/MQTTSummaryService` | 80% |
| `services/UserService` | 63% |
| `services/GoogleOAuthService` | 61% |
| `services/ScheduleService` | 59% |
| `services/EmployeeService` | 56% |
| `services/SSOService` | 55% |
| `services/EmailService` | 50% |
| `services/OllamaClient` | 42% |
| `services/GoogleCalendarService` | 35% |
| `services/MQTTClientManager` | 28% |
| `services/KafkaClientManager` | 23% |

#### Unit of Work Layer

| Module | Coverage |
|--------|----------|
| `unitofwork/KafkaUnitOfWork` | 100% |
| `unitofwork/MQTTUnitOfWork` | 100% |
| `unitofwork/UserUnitOfWork` | 100% |
| `unitofwork/ScheduleUnitOfWork` | 97% |
| `unitofwork/ApprovalUnitOfWork` | 97% |
| `unitofwork/SSOUnitOfWork` | 94% |
| `unitofwork/AssignEmployeeUnitOfWork` | 95% |
| `unitofwork/LoginRecordUnitOfWork` | 93% |
| `unitofwork/EmployeeUnitOfWork` | 93% |
| `unitofwork/ChatUnitOfWork` | 93% |
| `unitofwork/MessageUnitOfWork` | 93% |
| `unitofwork/WorkflowUnitOfWork` | 89% |

#### Router Layer

| Module | Coverage |
|--------|----------|
| `router/schemas/*` | 100% |
| `router/dependencies/auth` | 100% |
| `router/TasksRouter` | 100% |
| `router/ApprovalRouter` | 92% |
| `router/EmployeeRouter` | 89% |
| `router/SSORouter` | 78% |
| `router/UserRouter` | 77% |
| `router/ScheduleAgentService` | 75% |
| `router/MessageRouter` | 69% |
| `router/ChatRouter` | 64% |
| `router/KafkaRouter` | 64% |
| `router/MQTTRouter` | 64% |
| `router/OAuthRouter` | 67% |
| `router/SessionRouter` | 37% |
| `router/WorkFlowRouter` | 0% *(stub, not yet registered)* |

## Database Migrations

```bash
# Upgrade to latest
poetry run db-head

# Rollback all
poetry run db-base

# Auto-generate migration
poetry run alembic revision --autogenerate -m "description"
```

## API Endpoints

All endpoints are prefixed with `/api`.

### User Management (`/users`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/users/create` | Register new user (sends verification email) | Public |
| POST | `/users/login` | Login with uid/email + password | Public |
| GET | `/users/me` | Get current user profile | User |
| POST | `/users/profile/update` | Update profile | User |
| POST | `/users/update` | Change password | User |
| POST | `/users/avatar` | Upload avatar (jpg/png/gif/webp, max 5MB) | User |
| GET | `/users/` | List users with pagination | Admin |
| GET | `/users/search` | Search users by keyword | User |
| GET | `/users/verify-email` | Verify email with token | Public |
| POST | `/users/resend-verification` | Resend verification email | Public |
| POST | `/users/forgot-password` | Send password reset email | Public |
| POST | `/users/reset-password` | Reset password with token | Public |

### Google OAuth2 (`/auth`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/auth/google/login` | Redirect to Google consent screen | Public |
| GET | `/auth/google/callback` | OAuth2 callback | Public |
| POST | `/auth/google/token` | Exchange auth code for access token | Public |

### SSO (`/sso`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/sso/providers` | List active SSO providers | Public |
| GET | `/sso/login/{slug}` | Initiate SSO login (redirects to IdP) | Public |
| GET | `/sso/oidc/{slug}/callback` | OIDC callback | Public |
| POST | `/sso/saml/{slug}/acs` | SAML ACS endpoint | Public |
| POST | `/sso/token` | Exchange auth code for token | Public |
| GET | `/sso/saml/{slug}/metadata` | SP SAML metadata XML | Public |
| GET | `/sso/admin/providers` | List all providers | Admin |
| POST | `/sso/admin/providers` | Create SSO provider | Admin |
| GET | `/sso/admin/providers/{id}` | Get provider detail | Admin |
| PUT | `/sso/admin/providers/{id}` | Update provider | Admin |
| DELETE | `/sso/admin/providers/{id}` | Delete provider | Admin |
| POST | `/sso/admin/providers/{id}/activate` | Activate provider | Admin |
| POST | `/sso/admin/providers/{id}/deactivate` | Deactivate provider | Admin |
| GET | `/sso/admin/config` | Get SSO config | Admin |
| PUT | `/sso/admin/config` | Update SSO config | Admin |

### Employee Management (`/employees`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/employees/` | List employees with pagination | Admin |
| POST | `/employees/assign` | Assign user as employee | Admin |
| POST | `/employees/upload-csv` | Batch import from CSV (sync) | Admin |
| POST | `/employees/upload-csv-async` | Batch import from CSV (async via Celery) | Admin |

### Messaging (`/messages`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/messages/` | Send a message | User |
| POST | `/messages/{id}/reply` | Reply to a message | User |
| GET | `/messages/inbox` | Get inbox | User |
| GET | `/messages/sent` | Get sent messages | User |
| GET | `/messages/unread-count` | Get unread count | User |
| GET | `/messages/thread/{id}` | Get message thread | User |
| GET | `/messages/{id}` | Get message detail | User |
| PUT | `/messages/{id}/read` | Mark as read | User |
| PUT | `/messages/batch-read` | Batch mark as read | User |
| DELETE | `/messages/{id}` | Delete message (soft) | User |

### Schedule & Google Calendar (`/schedules`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/schedules/` | Create schedule | Employee |
| GET | `/schedules/` | List schedules | Employee |
| GET | `/schedules/{id}` | Get schedule detail | Employee |
| PUT | `/schedules/{id}` | Update schedule | Creator |
| DELETE | `/schedules/{id}` | Delete schedule | Creator |
| POST | `/schedules/{id}/sync` | Sync to Google Calendar | Creator |
| GET | `/schedules/google/status` | Google Calendar connection status | Admin |
| GET | `/schedules/google/auth` | Get Google OAuth URL | Admin |
| GET | `/schedules/google/callback` | Google OAuth callback | Public |
| GET | `/schedules/google/calendars` | List Google Calendars | Admin |
| POST | `/schedules/google/calendars/{id}/select` | Select calendar | Admin |
| POST | `/schedules/google/connect` | Connect Google Calendar | Admin |
| DELETE | `/schedules/google/disconnect` | Disconnect Google Calendar | Admin |

### AI Chat - Scheduling Assistant (`/chat`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/chat/` | Send message to AI assistant | Employee |
| GET | `/chat/conversations` | List conversations | Employee |
| GET | `/chat/conversations/{id}` | Get conversation messages | Employee |
| DELETE | `/chat/conversations/{id}` | Delete conversation | Employee |

### AI Chat - HR Approval Assistant (`/hr-chat`)

A conversational interface for managers to review and act on pending approval requests (leave, expense, etc.) using natural language. The LLM has access to 4 tools: list pending requests, get request detail, approve, and reject.

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/hr-chat/` | Send message to HR AI assistant | Employee |
| GET | `/hr-chat/conversations` | List conversations | Employee |
| GET | `/hr-chat/conversations/{id}` | Get conversation messages | Employee |
| DELETE | `/hr-chat/conversations/{id}` | Delete conversation | Employee |

### Background Tasks (`/tasks`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/tasks/status/{task_id}` | Get task status and progress | Admin |
| DELETE | `/tasks/cancel/{task_id}` | Cancel a running task | Admin |
| GET | `/tasks/add` | Demo: enqueue a test task | Admin |

### MQTT (`/mqtt`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/mqtt/status` | Connection status and subscriptions | Admin |
| POST | `/mqtt/publish` | Publish message to topic | Admin |
| POST | `/mqtt/subscriptions` | Subscribe to topic | Admin |
| GET | `/mqtt/subscriptions` | List active subscriptions | Admin |
| DELETE | `/mqtt/subscriptions/{topic}` | Unsubscribe from topic | Admin |
| GET | `/mqtt/messages` | Query stored messages (with pagination) | Admin |
| POST | `/mqtt/summary/trigger` | Manually trigger AI summary + email dispatch | Admin |

**Trigger request body** (`POST /mqtt/summary/trigger`):
```json
{ "hours": 24 }
```
`hours` is the look-back window (1–168, default 24). The endpoint enqueues a Celery task and returns the `task_id` immediately; poll `GET /tasks/status/{task_id}` for progress.

### Kafka (`/kafka`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/kafka/status` | Connection status and subscriptions | Admin |
| POST | `/kafka/produce` | Produce message to topic | Admin |
| POST | `/kafka/subscriptions` | Subscribe to topic (starts consumer) | Admin |
| GET | `/kafka/subscriptions` | List active subscriptions | Admin |
| DELETE | `/kafka/subscriptions/{topic}` | Unsubscribe from topic | Admin |
| GET | `/kafka/messages` | Query stored messages (with pagination) | Admin |

## Project Structure

```
fastapi-demo/
├── app/
│   ├── domain/                    # Domain models (business logic)
│   │   ├── UserModel.py
│   │   ├── EmployeeModel.py
│   │   ├── EmployeeCsvImportModel.py
│   │   ├── AuthorityModel.py
│   │   ├── MessageModel.py
│   │   ├── ScheduleModel.py
│   │   ├── ChatModel.py
│   │   ├── SSOModel.py
│   │   ├── MQTTModel.py
│   │   └── KafkaModel.py
│   ├── repositories/              # Data access layer
│   │   └── sqlalchemy/
│   ├── services/                  # Business logic orchestration
│   │   ├── unitofwork/            # Transaction management
│   │   ├── AuthService.py
│   │   ├── UserService.py
│   │   ├── EmployeeService.py
│   │   ├── MessageService.py
│   │   ├── ScheduleService.py
│   │   ├── SSOService.py
│   │   ├── SSOAdminService.py
│   │   ├── GoogleOAuthService.py
│   │   ├── GoogleCalendarService.py
│   │   ├── ScheduleAgentService.py  # AI scheduling assistant
│   │   ├── ApprovalAgentService.py  # AI HR approval assistant
│   │   ├── MQTTSummaryService.py    # MQTT digest: fetch → AI summarize → email
│   │   ├── OllamaClient.py          # Ollama LLM client
│   │   ├── EmailService.py
│   │   ├── FileUploadService.py   # S3/MinIO storage
│   │   ├── MQTTClientManager.py   # MQTT client singleton
│   │   ├── MQTTService.py
│   │   ├── KafkaClientManager.py  # Kafka producer/consumer singleton
│   │   └── KafkaService.py
│   ├── router/                    # API endpoints
│   │   ├── schemas/               # Pydantic request/response schemas
│   │   ├── dependencies/          # Auth dependencies
│   │   ├── UserRouter.py
│   │   ├── EmployeeRouter.py
│   │   ├── OAuthRouter.py
│   │   ├── SSORouter.py
│   │   ├── MessageRouter.py
│   │   ├── ScheduleRouter.py
│   │   ├── ChatRouter.py
│   │   ├── HRChatRouter.py
│   │   ├── TasksRouter.py
│   │   ├── MQTTRouter.py
│   │   └── KafkaRouter.py
│   ├── tasks/                     # Celery background tasks (add_tasks, employee_tasks, mqtt_summary_tasks)
│   ├── exceptions/                # Custom exceptions
│   ├── utils/                     # Utility functions
│   ├── config.py                  # Configuration management
│   ├── db.py                      # Database setup
│   ├── logger.py                  # Logging configuration
│   └── app.py                     # FastAPI application + lifespan
├── database/
│   ├── models/                    # SQLAlchemy ORM models
│   └── alembic/                   # Database migrations
├── tests/
│   ├── unit/
│   │   ├── domain/
│   │   ├── repo/
│   │   ├── service/
│   │   └── unitofwork/
│   └── integration/
├── mosquitto/config/              # Mosquitto broker config
├── nginx/                         # Nginx configuration
├── scripts/                       # Utility scripts
├── docker-compose.yaml
├── pyproject.toml
└── alembic.ini
```

## Architecture

This project follows **Domain-Driven Design** with clear separation of concerns:

### Domain Layer (`app/domain/`)
- Pure Python dataclasses with business logic
- No dependencies on infrastructure
- Factory methods for entity creation
- Domain validation and invariants

### Infrastructure Layer (`database/models/`)
- SQLAlchemy ORM models
- Database schema definitions
- Separated from domain logic

### Repository Layer (`app/repositories/`)
- Abstracts data access
- Maps between domain models and ORM entities

### Service Layer (`app/services/`)
- Orchestrates business operations
- Uses Unit of Work for transaction management
- Coordinates between repositories and domain models

### API Layer (`app/router/`)
- FastAPI routers and endpoints
- Pydantic schemas for validation
- Request/response handling

## Security

- **JWT Authentication** with token expiry
- **Password Hashing** with bcrypt
- **Email Verification** for new registrations
- **OAuth2 / SSO** for third-party authentication
- **Role-Based Access Control** (Admin / Employee / User)
- **CORS** configurable cross-origin policies
- **Input Validation** via Pydantic schemas

## Logging

Structured logging with loguru:
- Log files: `./logs/fast-api-{date}.log`
- Rotation: 10 MB per file
- Retention: 10 days
- Compression: Automatic gzip
- Request IDs: Unique identifier per request

## License

This project is licensed under the MIT License.

## Authors

- [shaojhan](https://github.com/shaojhan)
