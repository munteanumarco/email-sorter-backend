#!/bin/bash

# Start the worker in the background
echo "Starting email sync worker..."
python -m app.worker &
WORKER_PID=$!

# Wait a moment for worker to start
sleep 2

# Start the FastAPI app
echo "Starting FastAPI application..."
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT