# Email Sorter Backend

A FastAPI-based backend service that helps users automatically organize their Gmail accounts using AI-powered email categorization.

## 👋 Hey There!

This is my backend implementation for the paid challenge! I've built it using FastAPI and deployed it on Render's free tier. Quick heads up - since it's on the free tier, the first request might take a few seconds as the service spins up from its sleep state. But once it's warmed up, everything runs smoothly!

I had a great time building this, especially figuring out the OAuth flows, background syncing logic, and integrating the AI classification. While there's always room for improvement given also the short period of time (like moving from polling to pub/sub), I think this implementation provides a solid foundation for email organization and management.

## 🏗️ Architecture

### Core Components

- **FastAPI Application**: RESTful API service handling authentication, Gmail account management, and email categorization
- **Background Worker**: Periodic email sync process running alongside the main application
- **PostgreSQL Database**: Stores user data, Gmail accounts, emails, and categories
- **OpenAI Integration**: AI-powered email classification using GPT models

### Key Features

#### Multi-Account Management
- Users can connect one primary Gmail account for authentication
- Additional Gmail accounts can be connected for email management
- Each account maintains its own OAuth2 credentials and sync status

#### Email Synchronization
- Background worker polls Gmail accounts every minute for new emails
- Emails are downloaded, processed, and categorized automatically
- Sync status and timestamps are maintained per account

#### AI-Powered Classification
- Uses OpenAI's GPT models to analyze email content
- Automatically categorizes emails based on their content and context
- Intelligent summarization of email content for better organization
- Adapts to user-defined categories for personalized sorting

#### Authentication & Security
- Google OAuth2 for both authentication and Gmail API access
- JWT-based session management
- Separate OAuth2 flows for primary (auth) and secondary (connect) accounts

## 🚀 Deployment

Currently deployed on Render.com with:
- Web service running both API and worker - since on free tier render wont let me create a separate background service - thats why I went with this solution.
- PostgreSQL database
- Environment variables for configuration
- Automatic deployments from main branch

## 🛠️ Development

Available commands in Makefile:
```bash
make build      # Build Docker containers
make up         # Start services
make down       # Stop services
make test       # Run tests
make logs       # View logs
```

Docker Compose services:
- `api`: FastAPI application + background worker
- `db`: PostgreSQL database

## 🧪 Tests

The project includes basic unit tests covering core functionality. To run the tests:

```bash
# Using make
make test

# Or directly with pytest
python -m pytest -v
```

Current test coverage includes:
- Model relationships (User, Category, Email, GmailAccount)
- Basic CRUD operations
- Service layer functionality

Tests use SQLite in-memory database and mock external services (OpenAI, Gmail API) for speed and reliability.

### Test Structure
```
tests/
├── conftest.py           # Test configuration and fixtures
├── test_models.py        # Database model tests
└── test_services.py      # Service layer tests
```

## ⚠️ Limitations & Future Improvements

### Current Limitations
- Polling-based sync (1-minute intervals)
- Sequential email processing
- Rate limits based on Gmail API quotas

### Potential Improvements
1. **Real-time Updates**
   - Replace polling with Gmail Push Notifications
   - Implement WebSocket/SSE for frontend updates
   - Pub/Sub system for scalable event handling

2. **Testing**
   - Currently only basic unit tests
   - Add integration tests
   - Add CI/CD pipeline with test automation
   - Add API endpoint tests
   - Add worker process tests

3. **Performance & Scalability**
   - Parallel email processing
   - Batch API requests
   - Caching frequently accessed data
   - Separate worker processes per account

Feel free to explore the code and let me know if you have any questions! 🚀