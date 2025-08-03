## 👋 Hey There!

This is my backend implementation for the paid challenge! I've built it using FastAPI and deployed it on Render's free tier. Quick heads up - since it's on the free tier, the first request might take a few seconds as the service spins up from its sleep state. But once it's warmed up, everything runs smoothly!

The approach I took focuses on flexibility and user experience - you can connect your main Gmail account for authentication and then add as many additional accounts as you want for email management. Each account gets its own background sync process, and everything stays organized in your personal dashboard.

I had a great time building this, especially figuring out the OAuth flows and background syncing logic. While there's always room for improvement given also the short period of time (like moving from polling to pub/sub), I think this implementation provides a solid foundation for email organization and management.

Feel free to explore the code and let me know if you have any questions! 🚀

# Email Sorter Backend

A FastAPI-based backend service that helps users automatically organize their Gmail accounts using AI-powered email categorization.

## 🏗️ Architecture

### Core Components

- **FastAPI Application**: RESTful API service handling authentication, Gmail account management, and email categorization
- **Background Worker**: Periodic email sync process running alongside the main application
- **PostgreSQL Database**: Stores user data, Gmail accounts, emails, and categories

### Key Features

#### Multi-Account Management
- Users can connect one primary Gmail account for authentication
- Additional Gmail accounts can be connected for email management
- Each account maintains its own OAuth2 credentials and sync status

#### Email Synchronization
- Background worker polls Gmail accounts every minute for new emails
- Emails are downloaded, processed, and categorized automatically
- Sync status and timestamps are maintained per account

#### Authentication & Security
- Google OAuth2 for both authentication and Gmail API access
- JWT-based session management
- Separate OAuth2 flows for primary (auth) and secondary (connect) accounts

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- PostgreSQL
- Google Cloud Project with Gmail API enabled
- Google OAuth2 credentials

### Environment Variables
```env
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
```

### Installation
```bash
# Clone the repository
git clone [repository-url]

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the application (development)
uvicorn app.main:app --reload
```

## 📐 API Design

### Key Endpoints

- `/api/v1/auth/*`: Authentication and OAuth2 flows
- `/api/v1/gmail-accounts/*`: Gmail account management
- `/api/v1/emails/*`: Email operations and categorization
- `/api/v1/categories/*`: Category management

## 🔄 Sync Process

1. Worker process runs alongside the main application
2. Every minute, checks each connected Gmail account
3. Fetches new emails using Gmail API
4. Processes and categorizes emails
5. Updates sync status and timestamps

## 🛠️ Technical Implementation

### Authentication Flow
1. User initiates Google OAuth2 login
2. Backend receives OAuth2 callback with authorization code
3. Exchanges code for access/refresh tokens
4. Creates user account if new, or updates existing
5. Issues JWT session token

### Account Connection Flow
1. Authenticated user initiates new account connection
2. Similar OAuth2 flow but stores as secondary account
3. Immediate sync triggered for new account
4. Account appears in user's account list

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

2. **Performance Optimization**
   - Parallel email processing
   - Batch API requests
   - Caching frequently accessed data

3. **Scalability**
   - Separate worker processes per account
   - Queue-based email processing
   - Horizontal scaling of workers

## 📚 Dependencies

- FastAPI: Web framework
- SQLAlchemy: ORM
- Alembic: Database migrations
- Google API Client: Gmail API integration
- PyJWT: JWT token handling
- Pydantic: Data validation
- uvicorn: ASGI server

## 🚀 Deployment

Currently deployed on Render.com with:
- Web service running both API and worker
- PostgreSQL database
- Environment variables for configuration
- Automatic deployments from main branch
