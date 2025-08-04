# Email Sorter Backend

A FastAPI-based backend service that helps users automatically organize their Gmail accounts using AI-powered email categorization and automated unsubscribe functionality.

## 👋 Hey There!

This is my backend implementation for the paid challenge! I've built it using FastAPI and deployed it on Render's free tier. Quick heads up - since it's on the free tier, the first request might take a few seconds as the service spins up from its sleep state. But once it's warmed up, everything runs smoothly!

I had a great time building this, especially figuring out the OAuth flows, background syncing logic, and integrating the AI classification. While there's always room for improvement given also the short period of time (like moving from polling to pub/sub), I think this implementation provides a solid foundation for email organization and management.

## 🏗️ Architecture

### Core Components

- **FastAPI Application**: RESTful API service handling authentication, Gmail account management, email categorization, and unsubscribe automation
- **Background Worker**: Periodic email sync process running alongside the main application
- **PostgreSQL Database**: Stores user data, Gmail accounts, emails, categories, and unsubscribe statuses
- **OpenAI Integration**: AI-powered email classification using GPT models
- **Browser-Use Integration**: Open-source browser automation agent that connects AI models (OpenAI) to browsers for automated unsubscribe flows
  - Uses Playwright for browser control
  - Leverages GPT-4 for intelligent navigation and form filling
  - Validates unsubscribe success with confidence scoring

## 🚀 Deployment

Currently deployed on Render.com with:
- Docker-based deployment for consistent environments
- Web service running both API and worker (combined due to free tier limitations - a production setup would separate these)
- PostgreSQL database
- Environment variables for configuration
- Automatic deployments from main branch

## 🧪 Tests

The project includes basic unit tests, though with the time constraints, this is an area with room for improvement:

- **Current Coverage**:
  - Core model relationships
  - Basic CRUD operations
  - Service layer functionality
  - Email categorization logic

- **Future Test Improvements**:
  - Integration tests for API endpoints
  - End-to-end testing for complete flows
  - CI/CD pipeline for automated testing
  - Browser automation test suite
  - Performance and load testing

## ⚠️ Limitations & Future Improvements

While I've focused on implementing the core requirements and handling common edge cases, there are some limitations and areas for improvement:

### Current Limitations
- Polling-based sync (1-minute intervals)
- Sequential email processing
- Rate limits based on Gmail API quotas
- Browser automation might fail on complex unsubscribe flows
- No retry mechanism for failed unsubscribe attempts
- Limited handling of JavaScript-heavy unsubscribe pages
- No handling of email confirmation for unsubscribe

### Potential Improvements
1. **Real-time Updates**
   - Replace polling with Gmail Push Notifications
   - Implement WebSocket/SSE for frontend updates
   - Pub/Sub system for scalable event handling

2. **Unsubscribe Flow**
   - Add retry mechanism with exponential backoff
   - Implement unsubscribe confirmation tracking
   - Support for multi-step unsubscribe flows
   - Handle JavaScript-rendered content better
   - Store screenshots of failed attempts for debugging

3. **Performance & Scalability**
   - Parallel email processing
   - Batch API requests
   - Caching frequently accessed data
   - Separate worker processes per account
   - Queue system for unsubscribe requests

Feel free to explore the code and let me know if you have any questions! 🚀