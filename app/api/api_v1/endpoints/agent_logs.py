from typing import List
from fastapi import APIRouter, Depends
from app.api.deps import get_db
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pydantic import BaseModel

router = APIRouter()

class AgentLog(BaseModel):
    type: str
    message: str
    timestamp: str
    agent_id: str | None = None
    task_id: str | None = None

@router.get("/latest/", response_model=List[AgentLog])
def get_latest_logs(db: Session = Depends(get_db)):
    # For now, we'll return the logs from the browser-use agent that are stored in memory
    # In a future iteration, we could store these in the database
    from app.services.unsubscribe import get_latest_agent_logs
    
    logs = get_latest_agent_logs()
    parsed_logs = []
    for log in logs:
        # Extract timestamp if available
        timestamp = datetime.now().isoformat()

        # Determine log type
        log_type = "info"
        if "ERROR" in log:
            log_type = "error"
        elif "WARNING" in log:
            log_type = "warning"
        elif any(x in log for x in ["cost", "Thinking", "Memory", "Eval"]):
            log_type = "debug"
        elif "SUCCESS" in log or "Successfully" in log:
            log_type = "success"

        # Extract message
        message = log
        if "] " in log:
            parts = log.split("] ", 1)
            if len(parts) > 1:
                message = parts[1]

        # Extract agent ID if available
        agent_id = None
        if "[browser_use.Agent🅰 " in log:
            try:
                agent_id = log.split("[browser_use.Agent🅰 ")[1].split(" ")[0]
            except:
                pass

        parsed_logs.append(
            AgentLog(
                type=log_type,
                message=message,
                timestamp=timestamp,
                agent_id=agent_id,
                task_id=None
            )
        )

    return parsed_logs

@router.get("/task/{task_id}/", response_model=List[AgentLog])
def get_logs_by_task(task_id: str, db: Session = Depends(get_db)):
    # TODO: Implement fetching logs by task ID
    return []

@router.get("/agent/{agent_id}/", response_model=List[AgentLog])
def get_logs_by_agent(agent_id: str, db: Session = Depends(get_db)):
    # TODO: Implement fetching logs by agent ID
    return []