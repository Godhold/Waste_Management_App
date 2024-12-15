from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from datetime import datetime
from ..model import Driver , WasteCollection , Route , CustomerLocation
from ..database import get_db
from pydantic import BaseModel, constr

router = APIRouter()

# Pydantic models for request/response
class WasteCollectionBase(BaseModel):
    location_name: str
    address: str
    latitude: float
    longitude: float
    scheduled_time: datetime
    status: str = "PENDING"
    notes: Optional[str] = None

class WasteCollectionCreate(WasteCollectionBase):
    driver_id: int

class WasteCollectionUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    actual_collection_time: Optional[datetime] = None

class WasteCollectionResponse(WasteCollectionBase):
    id: int
    driver_id: int
    created_at: datetime
    updated_at: datetime
    actual_collection_time: Optional[datetime] = None

    class Config:
        from_attributes = True

class PaginatedCollectionResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[WasteCollectionResponse]

@router.get('/', response_model=PaginatedCollectionResponse)
def get_collections(
    search: Optional[str] = None,
    status: Optional[str] = None,
    driver_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(WasteCollection)
    
    # Apply filters
    if search:
        query = query.filter(
            or_(
                WasteCollection.location_name.ilike(f"%{search}%"),
                WasteCollection.address.ilike(f"%{search}%")
            )
        )
    
    if status:
        query = query.filter(WasteCollection.status == status)
    
    if driver_id:
        query = query.filter(WasteCollection.driver_id == driver_id)
    
    if start_date:
        query = query.filter(WasteCollection.scheduled_time >= start_date)
    
    if end_date:
        query = query.filter(WasteCollection.scheduled_time <= end_date)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": query.all()
    }

@router.post('/', response_model=WasteCollectionResponse, status_code=status.HTTP_201_CREATED)
def create_collection(collection: WasteCollectionCreate, db: Session = Depends(get_db)):
    # Verify driver exists and is active
    driver = db.query(Driver).filter(Driver.id == collection.driver_id).first()
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Driver with ID {collection.driver_id} not found"
        )
    if not driver.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Driver with ID {collection.driver_id} is not active"
        )
    
    db_collection = WasteCollection(**collection.model_dump())
    db.add(db_collection)
    db.commit()
    db.refresh(db_collection)
    return db_collection

@router.get('/{collection_id}', response_model=WasteCollectionResponse)
def get_collection(collection_id: int, db: Session = Depends(get_db)):
    collection = db.query(WasteCollection).filter(WasteCollection.id == collection_id).first()
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection with ID {collection_id} not found"
        )
    return collection

@router.put('/{collection_id}', response_model=WasteCollectionResponse)
def update_collection(
    collection_id: int,
    collection_update: WasteCollectionUpdate,
    db: Session = Depends(get_db)
):
    db_collection = db.query(WasteCollection).filter(WasteCollection.id == collection_id).first()
    if not db_collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection with ID {collection_id} not found"
        )
    
    update_data = collection_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_collection, field, value)
    
    db_collection.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_collection)
    return db_collection

@router.delete('/{collection_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_collection(collection_id: int, db: Session = Depends(get_db)):
    db_collection = db.query(WasteCollection).filter(WasteCollection.id == collection_id).first()
    if not db_collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection with ID {collection_id} not found"
        )
    
    db.delete(db_collection)
    db.commit()
    return None
