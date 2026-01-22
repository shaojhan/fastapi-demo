# FastAPI Demo

A production-ready FastAPI application following **Domain-Driven Design (DDD)** principles with a clean architecture, comprehensive testing, and enterprise-grade features.

## 🚀 Features

- **Domain-Driven Design**: Clean separation between domain logic, infrastructure, and application layers
- **Repository Pattern**: Abstract data access with domain model mapping
- **Unit of Work Pattern**: Transaction management and atomic operations
- **CQRS**: Separate read and write operations for optimal performance
- **JWT Authentication**: Secure user authentication with JWT tokens
- **Async Task Processing**: Celery + Redis for background job execution
- **Database Migrations**: Alembic for version-controlled schema changes
- **Comprehensive Testing**: Unit tests with 95%+ coverage
- **API Documentation**: Auto-generated Swagger UI and ReDoc
- **Structured Logging**: Request tracing with loguru
- **CI/CD**: GitHub Actions for automated testing

## 📋 Prerequisites

- Python 3.12+
- Poetry (dependency management)
- MySQL/MariaDB
- Redis (for Celery)
- Docker (optional, for containerization)

## 🛠️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/shaojhan/fastapi-demo.git
cd fastapi-demo
```

### 2. Install dependencies

```bash
# Install Poetry if you haven't
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
poetry install
```

### 3. Configure environment

Create a `.env` file in the project root:

```env
# Application
ENV=dev
FASTAPI_TITLE=FastAPI Demo
DEBUG=true

# Database
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/fastapi_demo

# Security
JWT_KEY=your-secret-jwt-key-here
SESSIONMIDDLEWARE_SECRET_KEY=your-session-secret-key

# Server
SERVER_IP=0.0.0.0

# Celery
BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Cache
CACHE_SERVER_HOST=localhost
CACHE_SERVER_PORT=6379
```

### 4. Initialize database

```bash
# Run migrations to create tables
poetry run db-head
```

## 🚀 Running the Application

### Development Server

```bash
# Start with hot reload (default port 8000)
poetry run dev

# Custom port
poetry run dev -p 3000

# Disable hot reload
poetry run dev --no-reload
```

The API will be available at:
- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`
- OpenAPI JSON: `http://localhost:8000/api/openapi.json`

### Celery Worker

Start the Celery worker for background tasks:

```bash
celery -A app.celery_worker worker --loglevel=info
```

### Nginx (Optional)

Run nginx reverse proxy:

```bash
poetry run nginx
```

## 🧪 Testing

### Run all tests

```bash
poetry run test
```

### Run specific test suites

```bash
# Domain tests
pytest tests/unit/domain/ -v

# Repository tests
pytest tests/unit/repo/ -v

# Service tests
pytest tests/unit/service/ -v

# Specific test file
pytest tests/unit/domain/test_employee_domain.py -v
```

### Test coverage

```bash
# Generate coverage report
pytest tests/unit/ --cov=app --cov-report=term-missing

# HTML coverage report
pytest tests/unit/ --cov=app --cov-report=html
```

## 📦 Database Migrations

### Apply migrations

```bash
# Upgrade to latest version
poetry run db-head

# Rollback all migrations
poetry run db-base
```

### Create new migration

```bash
# Auto-generate migration from model changes
poetry run alembic revision --autogenerate -m "description of changes"

# Create empty migration
poetry run alembic revision -m "description"
```

## 🏗️ Project Structure

```
fastapi-demo/
├── app/                          # Application code
│   ├── domain/                   # Domain models (business logic)
│   │   ├── EmployeeModel.py
│   │   ├── AuthorityModel.py
│   │   └── UserModel.py
│   ├── repositories/             # Data access layer
│   │   └── sqlalchemy/
│   │       ├── EmployeeRepository.py
│   │       ├── UserRepository.py
│   │       └── BaseRepository.py
│   ├── services/                 # Business logic orchestration
│   │   ├── EmployeeService.py
│   │   ├── UserService.py
│   │   └── unitofwork/          # Transaction management
│   │       ├── EmployeeUnitOfWork.py
│   │       └── UserUnitOfWork.py
│   ├── router/                   # API endpoints
│   │   ├── UserRouter.py
│   │   ├── WorkFlowRouter.py
│   │   └── schemas/             # Pydantic request/response schemas
│   ├── exceptions/              # Custom exceptions
│   ├── utils/                   # Utility functions
│   ├── config.py                # Configuration management
│   ├── db.py                    # Database setup
│   ├── logger.py                # Logging configuration
│   └── app.py                   # FastAPI application
├── database/                     # Database layer
│   ├── models/                  # SQLAlchemy ORM models
│   │   ├── employee.py
│   │   ├── role.py
│   │   ├── authority.py
│   │   └── user.py
│   └── alembic/                 # Database migrations
│       └── versions/
├── tests/                       # Test suite
│   ├── unit/                    # Unit tests
│   │   ├── domain/             # Domain model tests
│   │   ├── repo/               # Repository tests
│   │   └── service/            # Service tests
│   ├── integration/            # Integration tests
│   └── e2e/                    # End-to-end tests
├── scripts/                     # Utility scripts
├── nginx/                       # Nginx configuration
├── logs/                        # Application logs
├── .github/workflows/          # CI/CD workflows
├── pyproject.toml              # Poetry dependencies
├── alembic.ini                 # Alembic configuration
└── README.md
```

## 🏛️ Architecture

This project follows **Domain-Driven Design** with clear separation of concerns:

### Domain Layer (`app/domain/`)
- Pure Python dataclasses with business logic
- No dependencies on infrastructure
- Factory methods for entity creation
- Domain validation and invariants
- Examples: `EmployeeModel.create()`, `employee.assign_role()`

### Infrastructure Layer (`database/models/`)
- SQLAlchemy ORM models
- Database schema definitions
- Relationships and constraints
- Separated from domain logic

### Repository Layer (`app/repositories/`)
- Abstracts data access
- Maps between domain models and ORM entities
- Provides clean interfaces for data operations
- Implements both command and query repositories

### Service Layer (`app/services/`)
- Orchestrates business operations
- Uses Unit of Work for transaction management
- Coordinates between repositories and domain models
- Contains application-specific logic

### API Layer (`app/router/`)
- FastAPI routers and endpoints
- Pydantic schemas for validation
- Request/response handling
- Minimal business logic

## 🔑 Key Design Patterns

### Repository Pattern
Separates domain models from data persistence:
```python
# Domain model
employee = EmployeeModel.create(idno="EMP001", department=Department.IT)

# Repository saves it
with EmployeeUnitOfWork() as uow:
    created = uow.repo.add(employee)
    uow.commit()
```

### Unit of Work Pattern
Manages transactions and maintains consistency:
```python
with EmployeeUnitOfWork() as uow:
    employee = uow.repo.get_by_id(1)
    employee.assign_role(...)
    uow.repo.update(employee)
    uow.commit()  # Atomic transaction
```

### CQRS (Command Query Responsibility Segregation)
Separate services for reads and writes:
```python
# Command (write)
employee_service = EmployeeService()
employee_service.create_employee(...)

# Query (read)
query_service = EmployeeQueryService()
admins = query_service.get_employees_with_authority("ADMIN")
```

## 📚 API Endpoints

### User Management
- `POST /api/users/register` - Register new user
- `POST /api/users/login` - User login
- `GET /api/users/profile` - Get user profile

### Employee Management
- `POST /api/employees` - Create employee
- `GET /api/employees/{id}` - Get employee by ID
- `PUT /api/employees/{id}/role` - Assign role to employee
- `PUT /api/employees/{id}/department` - Change department
- `GET /api/employees/department/{dept}` - Get employees by department

### Workflow
- `POST /api/workflows` - Create workflow
- `GET /api/workflows/{id}` - Get workflow status

## 🔒 Security

- **JWT Authentication**: Secure token-based auth
- **Password Hashing**: bcrypt with salt
- **CORS**: Configurable cross-origin policies
- **Input Validation**: Pydantic schema validation
- **SQL Injection Protection**: Parameterized queries via SQLAlchemy

## 📊 Logging

Structured logging with request tracing:
- Log files: `./logs/fast-api-{date}.log`
- Rotation: 10 MB per file
- Retention: 10 days
- Compression: Automatic gzip
- Request IDs: Unique identifier per request

## 🔄 CI/CD

GitHub Actions workflow for automated testing:
- Runs on push and pull requests
- Python 3.12 environment
- Installs dependencies with Poetry
- Executes full test suite
- Reports test results

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Commit Message Convention

Follow the commit message format:
```
<type>: <subject>

<body>

Co-Authored-By: Name <email>
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`

## 📝 License

This project is licensed under the MIT License.

## 👥 Authors

- **Jhan** - *Initial work* - [shaojhan](https://github.com/shaojhan)

## 🙏 Acknowledgments

- FastAPI framework and community
- SQLAlchemy ORM
- Domain-Driven Design principles
- Clean Architecture patterns

## 📞 Support

For issues and questions:
- Create an issue on GitHub
- Email: eletronicphysic0907@gmail.com

---

Built with ❤️ using FastAPI and Domain-Driven Design
