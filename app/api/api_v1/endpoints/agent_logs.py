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
    return [
        AgentLog(
            type="info" if "INFO" in log else "error" if "ERROR" in log else "warning" if "WARNING" in log else "debug",
            message=log.split("] ", 1)[1] if "] " in log else log,
            timestamp=datetime.now().isoformat(),
            agent_id=log.split("[browser_use.Agent🅰 ")[1].split(" ")[0] if "[browser_use.Agent🅰 " in log else None,
            task_id=None
        )
        for log in logs
    ]

@router.get("/task/{task_id}/", response_model=List[AgentLog])
def get_logs_by_task(task_id: str, db: Session = Depends(get_db)):
    # TODO: Implement fetching logs by task ID
    return []

@router.get("/agent/{agent_id}/", response_model=List[AgentLog])
def get_logs_by_agent(agent_id: str, db: Session = Depends(get_db)):
    # TODO: Implement fetching logs by agent ID
    return []