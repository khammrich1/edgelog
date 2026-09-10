# EdgeLog Development Setup

This guide will help you set up EdgeLog for local development.

## Prerequisites

- Python 3.11+
- PostgreSQL 16+
- Node.js 18+ and npm
- Git

## Backend Setup

### 1. Install PostgreSQL

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# macOS
brew install postgresql
```

### 2. Create Databases

```bash
# Start PostgreSQL service
sudo service postgresql start  # Linux
brew services start postgresql  # macOS

# Create databases
sudo -u postgres psql -c "CREATE DATABASE edgelog_dev;"
sudo -u postgres psql -c "CREATE DATABASE edgelog_test;"
sudo -u postgres psql -c "CREATE USER edgelog WITH PASSWORD 'your_secure_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE edgelog_dev TO edgelog;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE edgelog_test TO edgelog;"

# Grant schema permissions (PostgreSQL 15+)
sudo -u postgres psql -d edgelog_dev -c "GRANT ALL ON SCHEMA public TO edgelog; GRANT CREATE ON SCHEMA public TO edgelog;"
sudo -u postgres psql -d edgelog_test -c "GRANT ALL ON SCHEMA public TO edgelog; GRANT CREATE ON SCHEMA public TO edgelog;"
```

### 3. Set Up Python Environment

```bash
cd backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your settings
nano .env
```

Required environment variables:
```bash
DATABASE_URL=postgresql+asyncpg://edgelog:your_secure_password@localhost/edgelog_dev
SECRET_KEY=your_generated_secret_key  # Generate with: python3 -c "import secrets; print(secrets.token_urlsafe(32))"
ALLOWED_ORIGINS=["http://localhost:5173", "http://localhost:3000"]
```

### 5. Run Database Migrations

```bash
# Make sure you're in the backend directory with venv activated
alembic upgrade head
```

### 6. Run Backend Tests

```bash
# Set PYTHONPATH and run tests
PYTHONPATH=/path/to/edgelog/backend pytest app/tests/ -v
```

All 9 tests should pass:
- ✅ test_register_new_user
- ✅ test_register_duplicate_email
- ✅ test_login_success
- ✅ test_login_wrong_password
- ✅ test_login_nonexistent_user
- ✅ test_protected_route_requires_token
- ✅ test_protected_route_with_valid_token
- ✅ test_refresh_token_flow
- ✅ test_logout_clears_refresh_token

### 7. Start Backend Server

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at http://localhost:8000

## Frontend Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Configure Environment

```bash
# Create local environment file
echo "VITE_API_URL=http://localhost:8000" > .env.local
```

### 3. Start Development Server

```bash
npm run dev
```

Frontend will be available at http://localhost:5173

### 4. Build for Production

```bash
npm run build
```

Production build will be in `frontend/dist/`

## Verifying Your Setup

### 1. Backend Health Check

```bash
# Register a test user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpassword123"}'

# Expected response: {"access_token":"...","token_type":"bearer"}
```

### 2. Frontend Login Test

1. Navigate to http://localhost:5173
2. Click "Create Account" 
3. Register with an email and password (8+ characters)
4. You should be redirected to the journal placeholder page
5. Verify the EdgeLog logo and "Find Your Edge" tagline appear
6. Click "Logout" to verify it works

## Development Workflow

### Making Database Changes

```bash
# Create a new migration
alembic revision -m "description of changes"

# Edit the generated migration file in backend/alembic/versions/

# Apply the migration
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

### Running Tests During Development

```bash
# Backend tests (run from backend directory with venv activated)
PYTHONPATH=/path/to/edgelog/backend pytest app/tests/ -v

# Watch mode for continuous testing
PYTHONPATH=/path/to/edgelog/backend pytest-watch app/tests/
```

### Code Style

Backend:
- Follow PEP 8 style guide
- Use type hints
- Async/await for all database operations

Frontend:
- Vue 3 Composition API (`<script setup>`)
- Pinia for state management
- CSS variables from design tokens

## Project Structure

```
edgelog/
├── backend/
│   ├── alembic/           # Database migrations
│   ├── app/
│   │   ├── api/           # API endpoints
│   │   ├── core/          # Config, database, security
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   └── tests/         # Pytest test suite
│   ├── requirements.txt   # Python dependencies
│   └── .env               # Environment configuration
├── frontend/
│   ├── public/            # Static assets
│   ├── src/
│   │   ├── assets/        # Styles and design tokens
│   │   ├── components/    # Vue components
│   │   ├── router/        # Vue Router
│   │   ├── services/      # API client
│   │   ├── stores/        # Pinia stores
│   │   └── views/         # Page components
│   └── package.json       # Node dependencies
└── README.md
```

## Common Issues

### Backend won't start
- Check PostgreSQL is running: `sudo service postgresql status`
- Verify DATABASE_URL in .env is correct
- Ensure migrations are up to date: `alembic upgrade head`

### Frontend API calls fail
- Verify backend is running on port 8000
- Check VITE_API_URL in .env.local
- Look for CORS errors in browser console (check ALLOWED_ORIGINS in backend .env)

### Tests fail with permission errors
- Grant proper PostgreSQL permissions (see step 2 above)
- Ensure test database exists and is accessible

### Cannot connect to database
- Check PostgreSQL is running
- Verify database user has proper permissions
- Test connection: `psql -U edgelog -d edgelog_dev -h localhost`

## VS1 Features Available

✅ User registration and login
✅ JWT authentication with refresh tokens
✅ HttpOnly cookie security
✅ App shell with navigation and logout
✅ EdgeLog branding and design system
✅ Toast notifications

⏳ Not yet implemented (future vertical slices):
- Trading days calendar (VS2)
- Trade entry and management (VS3+)
- Analytics and psychology tracking (VS4+)
- XP system, AI features, social features (VS11+)

## Getting Help

- Check the project README.md for architecture overview
- Review test files in app/tests/ for API usage examples
- See DEPLOYMENT.md for production deployment
