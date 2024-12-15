from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
from ..model import Driver, WasteCollection
from ..database import get_db
from pydantic import BaseModel

router = APIRouter()

class LocationUpdate(BaseModel):
    latitude: float
    longitude: float
    timestamp: datetime = datetime.utcnow()

class TrackingResponse(BaseModel):
    driver_id: int
    collection_id: Optional[int]
    driver_name: str
    current_location: dict
    current_task: Optional[dict]
    last_update: datetime

@router.get('/live', response_model=List[TrackingResponse])
def get_live_tracking(
    driver_id: Optional[int] = None,
    collection_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Driver)
    
    if driver_id:
        query = query.filter(Driver.id == driver_id)
    
    drivers = query.all()
    tracking_data = []
    
    for driver in drivers:
        # Get current active collection for driver
        current_collection = (
            db.query(WasteCollection)
            .filter(
                WasteCollection.driver_id == driver.id,
                WasteCollection.status == "IN_PROGRESS"
            )
            .first()
        )
        
        tracking_info = {
            "driver_id": driver.id,
            "collection_id": current_collection.id if current_collection else None,
            "driver_name": driver.name,
            "current_location": {
                "latitude": driver.current_lat,
                "longitude": driver.current_lng
            },
            "current_task": {
                "location": current_collection.location_name,
                "status": current_collection.status,
                "scheduled_time": current_collection.scheduled_time
            } if current_collection else None,
            "last_update": driver.last_update
        }
        tracking_data.append(tracking_info)
    
    return tracking_data

@router.get('/history/{driver_id}')
def get_tracking_history(
    driver_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Driver with ID {driver_id} not found"
        )
    
    query = db.query(WasteCollection).filter(WasteCollection.driver_id == driver_id)
    
    if start_date:
        query = query.filter(WasteCollection.scheduled_time >= start_date)
    if end_date:
        query = query.filter(WasteCollection.scheduled_time <= end_date)
    
    collections = query.all()
    
    return {
        "driver_info": {
            "id": driver.id,
            "name": driver.name,
            "is_active": driver.is_active
        },
        "collections": [
            {
                "id": c.id,
                "location": c.location_name,
                "status": c.status,
                "scheduled_time": c.scheduled_time,
                "actual_collection_time": c.actual_collection_time
            }
            for c in collections
        ]
    }

@router.get('/analytics')
def get_tracking_analytics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    driver_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(WasteCollection)
    
    if start_date:
        query = query.filter(WasteCollection.scheduled_time >= start_date)
    if end_date:
        query = query.filter(WasteCollection.scheduled_time <= end_date)
    if driver_id:
        query = query.filter(WasteCollection.driver_id == driver_id)
    
    collections = query.all()
    
    total_collections = len(collections)
    completed_collections = len([c for c in collections if c.status == "COMPLETED"])
    pending_collections = len([c for c in collections if c.status == "PENDING"])
    in_progress_collections = len([c for c in collections if c.status == "IN_PROGRESS"])
    
    return {
        "period": {
            "start": start_date,
            "end": end_date
        },
        "metrics": {
            "total_collections": total_collections,
            "completed_collections": completed_collections,
            "pending_collections": pending_collections,
            "in_progress_collections": in_progress_collections,
            "completion_rate": (completed_collections / total_collections * 100) if total_collections > 0 else 0
        }
    }
