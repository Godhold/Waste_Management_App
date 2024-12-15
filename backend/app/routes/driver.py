from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile, Body
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from ..model import Driver, WasteCollection, CollectionPhoto, Route, CustomerLocation
from ..database import get_db
from pydantic import BaseModel, Field
import logging
from ..utils import save_upload_file
from ..utils.security import verify_password, get_password_hash
import os
from math import radians, sin, cos, sqrt, atan2

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

# Constants for status transitions
VALID_STATUS_TRANSITIONS = {
    "PENDING": ["IN_PROGRESS"],
    "IN_PROGRESS": ["COMPLETED", "SKIPPED"],
    "COMPLETED": [],
    "SKIPPED": []
}

# Enhanced validation for status transitions
def validate_status_transition(current_status: str, new_status: str) -> bool:
    if current_status not in VALID_STATUS_TRANSITIONS:
        return False
    return new_status in VALID_STATUS_TRANSITIONS[current_status]

# Pydantic models
class DriverSignup(BaseModel):
    name: str
    phone: str = Field(..., pattern=r'^\+233\d{9}$')
    email: str = Field(..., pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    password: str = Field(..., min_length=8)

class DriverLogin(BaseModel):
    email: str = Field(..., pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    password: str = Field(..., min_length=8)

class DriverProfile(BaseModel):
    id: int
    name: str
    phone: str
    email: str
    is_active: bool = True
    current_lat: Optional[float] = None
    current_lng: Optional[float] = None
    last_update: Optional[datetime] = None

    class Config:
        from_attributes = True

class CustomerLocationResponse(BaseModel):
    name: str
    address: str
    contact_name: str
    contact_number: str

    class Config:
        from_attributes = True

class CollectionResponse(BaseModel):
    id: int
    location_name: str
    address: str
    scheduled_time: datetime
    status: str
    notes: Optional[str]
    customer_location: Optional[CustomerLocationResponse]
    navigation: Optional[Dict] = None

    class Config:
        from_attributes = True

class CollectionStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None

class StatusUpdateResponse(BaseModel):
    message: str
    collection_id: int
    new_status: str

class PhotoUploadResponse(BaseModel):
    message: str
    photo_url: str
    collection_id: int

class RouteOptimizationResponse(BaseModel):
    optimized_collections: List[CollectionResponse]
    total_distance: float
    estimated_time: int

class DriverProfileUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = Field(None, pattern=r'^\+233\d{9}$')
    email: Optional[str] = Field(None, pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    current_lat: Optional[float] = None
    current_lng: Optional[float] = None

class PasswordChange(BaseModel):
    old_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8)

# Dashboard Response Models
class DailyStats(BaseModel):
    total_collections: int
    completed_collections: int
    pending_collections: int
    total_distance: float
    completion_rate: float
    average_time_per_collection: float

class WeeklyStats(BaseModel):
    collections_by_day: Dict[str, int]
    total_collections: int
    total_distance: float
    completion_rate: float
    busiest_day: str

class MonthlyStats(BaseModel):
    total_collections: int
    average_daily_collections: float
    total_distance: float
    completion_rate: float
    collections_by_week: Dict[str, int]

class PerformanceStats(BaseModel):
    daily: DailyStats
    weekly: WeeklyStats
    monthly: MonthlyStats

# Driver authentication endpoints
@router.post("/signup", response_model=DriverProfile)
async def signup_driver(driver_data: DriverSignup, db: Session = Depends(get_db)):
    # Check if driver with phone number or email already exists
    existing_driver = db.query(Driver).filter(
        (Driver.phone == driver_data.phone) | (Driver.email == driver_data.email)
    ).first()
    if existing_driver:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Driver with this phone number or email already exists"
        )
    
    # Create new driver with hashed password
    db_driver = Driver(
        name=driver_data.name,
        phone=driver_data.phone,
        email=driver_data.email,
        password=get_password_hash(driver_data.password),
        is_active=True
    )
    db.add(db_driver)
    db.commit()
    db.refresh(db_driver)
    
    return db_driver

@router.post("/login", response_model=DriverProfile)
async def login_driver(login_data: DriverLogin, db: Session = Depends(get_db)):
    # Find driver by email
    driver = db.query(Driver).filter(Driver.email == login_data.email).first()
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not verify_password(login_data.password, driver.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    return driver

# Profile Management Endpoints
@router.get("/profile/{driver_id}", response_model=DriverProfile)
async def get_driver_profile(driver_id: int, db: Session = Depends(get_db)):
    """Get driver profile information"""
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    return driver

@router.put("/profile/{driver_id}", response_model=DriverProfile)
async def update_driver_profile(
    driver_id: int,
    profile: DriverProfileUpdate,
    db: Session = Depends(get_db)
):
    """Update driver profile information"""
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    # Check if email already exists
    if profile.email and profile.email != driver.email:
        existing_driver = db.query(Driver).filter(Driver.email == profile.email).first()
        if existing_driver:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check if phone already exists
    if profile.phone and profile.phone != driver.phone:
        existing_driver = db.query(Driver).filter(Driver.phone == profile.phone).first()
        if existing_driver:
            raise HTTPException(status_code=400, detail="Phone number already registered")
    
    # Update fields
    for field, value in profile.dict(exclude_unset=True).items():
        setattr(driver, field, value)
    
    driver.last_update = datetime.utcnow()
    db.commit()
    db.refresh(driver)
    return driver

@router.put("/profile/{driver_id}/password")
async def change_password(
    driver_id: int,
    password_change: PasswordChange,
    db: Session = Depends(get_db)
):
    """Change driver password"""
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    # Verify old password
    if not verify_password(password_change.old_password, driver.password):
        raise HTTPException(status_code=400, detail="Incorrect password")
    
    # Update password
    driver.password = get_password_hash(password_change.new_password)
    driver.last_update = datetime.utcnow()
    db.commit()
    return {"message": "Password updated successfully"}

# Utility functions
def get_navigation_info(start_lat: float, start_lng: float, end_lat: float, end_lng: float) -> Dict:
    """Calculate navigation information between two points"""
    # Calculate direct distance using Haversine formula
    R = 6371  # Earth's radius in kilometers
    
    lat1, lon1, lat2, lon2 = map(radians, [start_lat, start_lng, end_lat, end_lng])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c
    
    # Estimate time (assuming average speed of 30 km/h in city)
    estimated_time = int((distance / 30) * 60)  # minutes
    
    return {
        "distance_km": round(distance, 2),
        "estimated_time_min": estimated_time,
        "start_location": {"lat": start_lat, "lng": start_lng},
        "end_location": {"lat": end_lat, "lng": end_lng}
    }

def optimize_collections(start_lat: float, start_lng: float, collections: List[WasteCollection]):
    """Optimize collection route using nearest neighbor algorithm"""
    unvisited = collections.copy()
    current_lat, current_lng = start_lat, start_lng
    optimized_collections = []
    total_distance = 0
    
    while unvisited:
        # Find nearest collection point
        nearest = min(
            unvisited,
            key=lambda x: calculate_distance(
                current_lat, current_lng,
                x.customer_location.latitude, x.customer_location.longitude
            )
        )
        
        # Calculate distance and add to total
        distance = calculate_distance(
            current_lat, current_lng,
            nearest.customer_location.latitude, nearest.customer_location.longitude
        )
        total_distance += distance
        
        # Add navigation info
        nearest.navigation = get_navigation_info(
            current_lat, current_lng,
            nearest.customer_location.latitude, nearest.customer_location.longitude
        )
        
        optimized_collections.append(nearest)
        unvisited.remove(nearest)
        current_lat, current_lng = nearest.customer_location.latitude, nearest.customer_location.longitude
    
    # Calculate total estimated time (assuming 30 km/h average speed plus 15 min per collection)
    total_time = int((total_distance / 30) * 60 + len(optimized_collections) * 15)
    
    return {
        "optimized_collections": optimized_collections,
        "total_distance": round(total_distance, 2),
        "estimated_time": total_time
    }

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points using Haversine formula"""
    R = 6371  # Earth's radius in kilometers
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

# Collection endpoints with navigation
@router.get("/collections", response_model=List[CollectionResponse])
async def get_driver_collections(db: Session = Depends(get_db)):
    """Get all collections assigned to the driver for today"""
    today = datetime.utcnow().date()
    collections = db.query(WasteCollection).join(
        CustomerLocation
    ).filter(
        and_(
            WasteCollection.scheduled_time >= today,
            WasteCollection.scheduled_time < today + timedelta(days=1),
            WasteCollection.driver_id == 1  # TODO: Get from auth token
        )
    ).all()
    
    # Add location details to each collection
    for collection in collections:
        collection.location_name = collection.customer_location.name
        collection.address = collection.customer_location.address
    
    return collections

@router.get("/collections/{collection_id}", response_model=CollectionResponse)
async def get_driver_collection_details(collection_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a specific collection with navigation"""
    collection = db.query(WasteCollection).join(
        CustomerLocation
    ).filter(
        and_(
            WasteCollection.id == collection_id,
            WasteCollection.driver_id == 1  # TODO: Get from auth token
        )
    ).first()
    
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    # Add location details
    collection.location_name = collection.customer_location.name
    collection.address = collection.customer_location.address
    
    # Add navigation info if driver has current location
    driver = db.query(Driver).filter(Driver.id == 1).first()  # TODO: Get from auth token
    if driver and driver.current_lat and driver.current_lng:
        collection.navigation = get_navigation_info(
            driver.current_lat,
            driver.current_lng,
            collection.customer_location.latitude,
            collection.customer_location.longitude
        )
    
    return collection

@router.get("/route/optimize", response_model=RouteOptimizationResponse)
async def optimize_route(db: Session = Depends(get_db)):
    """Get optimized route for today's collections"""
    today = datetime.utcnow().date()
    collections = db.query(WasteCollection).join(
        CustomerLocation
    ).filter(
        and_(
            WasteCollection.scheduled_time >= today,
            WasteCollection.scheduled_time < today + timedelta(days=1),
            WasteCollection.status == "PENDING",
            WasteCollection.driver_id == 1  # TODO: Get from auth token
        )
    ).all()
    
    if not collections:
        raise HTTPException(status_code=404, detail="No pending collections found")
    
    # Get driver's current location
    driver = db.query(Driver).filter(Driver.id == 1).first()
    start_lat = driver.current_lat if driver and driver.current_lat else 5.6037  # Default to Accra
    start_lng = driver.current_lng if driver and driver.current_lng else -0.1870
    
    # Add location details to collections
    for collection in collections:
        collection.location_name = collection.customer_location.name
        collection.address = collection.customer_location.address
    
    # Optimize route
    optimized_collections = collections  # For now, keep original order
    total_distance = 0
    
    # Calculate distances and add navigation info
    for i in range(len(optimized_collections)):
        if i == 0:
            # Distance from driver to first collection
            total_distance += calculate_distance(
                start_lat, start_lng,
                optimized_collections[i].customer_location.latitude,
                optimized_collections[i].customer_location.longitude
            )
            # Add navigation info for first collection
            optimized_collections[i].navigation = get_navigation_info(
                start_lat, start_lng,
                optimized_collections[i].customer_location.latitude,
                optimized_collections[i].customer_location.longitude
            )
        else:
            # Distance between consecutive collections
            total_distance += calculate_distance(
                optimized_collections[i-1].customer_location.latitude,
                optimized_collections[i-1].customer_location.longitude,
                optimized_collections[i].customer_location.latitude,
                optimized_collections[i].customer_location.longitude
            )
            # Add navigation info
            optimized_collections[i].navigation = get_navigation_info(
                optimized_collections[i-1].customer_location.latitude,
                optimized_collections[i-1].customer_location.longitude,
                optimized_collections[i].customer_location.latitude,
                optimized_collections[i].customer_location.longitude
            )
    
    # Estimate time (assuming average speed of 30 km/h)
    estimated_time = int((total_distance / 30) * 60)  # minutes
    
    return {
        "optimized_collections": optimized_collections,
        "total_distance": round(total_distance, 2),
        "estimated_time": estimated_time
    }

# Update collection status
@router.put("/collections/{collection_id}/status", response_model=StatusUpdateResponse)
async def update_collection_status(
    collection_id: int,
    status_update: CollectionStatusUpdate,
    db: Session = Depends(get_db)
):
    """Update the status of a collection"""
    collection = db.query(WasteCollection).filter(
        and_(
            WasteCollection.id == collection_id,
            WasteCollection.driver_id == 1  # TODO: Get from auth token
        )
    ).first()
    
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    # Validate status transition
    if not validate_status_transition(collection.status, status_update.status):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status transition from {collection.status} to {status_update.status}"
        )
    
    # Update status and notes
    collection.status = status_update.status
    if status_update.notes:
        collection.notes = status_update.notes
    
    db.commit()
    
    return {
        "message": "Status updated successfully",
        "collection_id": collection_id,
        "new_status": status_update.status
    }

# Upload collection photo
@router.post("/collections/{collection_id}/photos", response_model=PhotoUploadResponse)
async def upload_collection_photo(
    collection_id: int,
    photo_type: str = Query(..., regex="^(before|after)$"),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    collection = db.query(WasteCollection).filter(WasteCollection.id == collection_id).first()
    
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    # Check if photo of this type already exists
    existing_photo = db.query(CollectionPhoto).filter(
        and_(
            CollectionPhoto.collection_id == collection_id,
            CollectionPhoto.photo_type == photo_type
        )
    ).first()
    
    if existing_photo:
        raise HTTPException(
            status_code=400,
            detail=f"{photo_type.capitalize()} photo already exists for this collection"
        )
    
    # Save photo
    try:
        photo_url = await save_upload_file(photo, f"collection_{collection_id}_{photo_type}")
        
        # Create photo record
        db_photo = CollectionPhoto(
            collection_id=collection_id,
            photo_url=photo_url,
            photo_type=photo_type
        )
        db.add(db_photo)
        db.commit()
        
        return {
            "message": "Photo uploaded successfully",
            "photo_url": photo_url,
            "collection_id": collection_id
        }
    except Exception as e:
        logger.error(f"Error uploading photo: {str(e)}")
        raise HTTPException(status_code=500, detail="Error uploading photo")

# Dashboard Endpoints
@router.get("/dashboard/today", response_model=DailyStats)
async def get_today_stats(driver_id: int, db: Session = Depends(get_db)):
    """Get driver's statistics for today"""
    today = datetime.utcnow()
    today_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    # Get today's collections with customer location data
    collections = db.query(WasteCollection).options(
        joinedload(WasteCollection.customer_location)
    ).filter(
        and_(
            WasteCollection.driver_id == driver_id,
            WasteCollection.scheduled_time >= today_start,
            WasteCollection.scheduled_time < today_end
        )
    ).all()

    total_collections = len(collections)
    completed_collections = sum(1 for c in collections if c.status == "COMPLETED")
    pending_collections = sum(1 for c in collections if c.status == "PENDING")
    
    # Calculate total distance
    total_distance = 0
    if collections:
        for i, collection in enumerate(collections):
            if collection.customer_location:
                if i == 0:
                    # Distance from start point to first collection
                    total_distance += calculate_distance(
                        5.6037, -0.1870,  # Default Accra coordinates
                        collection.customer_location.latitude,
                        collection.customer_location.longitude
                    )
                else:
                    # Distance between consecutive collections
                    prev = collections[i-1].customer_location
                    curr = collection.customer_location
                    if prev and curr:
                        total_distance += calculate_distance(
                            prev.latitude, prev.longitude,
                            curr.latitude, curr.longitude
                        )

    # Calculate completion rate
    completion_rate = (completed_collections / total_collections * 100) if total_collections > 0 else 0
    
    # Calculate average time per collection (in minutes)
    avg_time = 0
    completed = [c for c in collections if c.status == "COMPLETED"]
    if completed:
        total_time = sum((c.last_update - c.scheduled_time).total_seconds() for c in completed)
        avg_time = (total_time / len(completed)) / 60  # Convert to minutes

    return {
        "total_collections": total_collections,
        "completed_collections": completed_collections,
        "pending_collections": pending_collections,
        "total_distance": round(total_distance, 2),
        "completion_rate": round(completion_rate, 2),
        "average_time_per_collection": round(avg_time, 2)
    }

@router.get("/dashboard/weekly", response_model=WeeklyStats)
async def get_weekly_stats(driver_id: int, db: Session = Depends(get_db)):
    """Get driver's statistics for the current week"""
    today = datetime.utcnow().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=7)

    collections = db.query(WasteCollection).options(
        joinedload(WasteCollection.customer_location)
    ).filter(
        and_(
            WasteCollection.driver_id == driver_id,
            WasteCollection.scheduled_time >= start_of_week,
            WasteCollection.scheduled_time < end_of_week
        )
    ).all()

    # Initialize collections by day
    collections_by_day = {day: 0 for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']}
    
    total_collections = len(collections)
    completed_collections = 0
    total_distance = 0
    
    for collection in collections:
        day = collection.scheduled_time.strftime('%A')
        collections_by_day[day] += 1
        if collection.status == "COMPLETED":
            completed_collections += 1
            
        # Calculate distance (simplified version)
        if collection.customer_location:
            total_distance += calculate_distance(
                5.6037, -0.1870,  # Default Accra coordinates
                collection.customer_location.latitude,
                collection.customer_location.longitude
            )

    # Find busiest day
    busiest_day = max(collections_by_day.items(), key=lambda x: x[1])[0] if any(collections_by_day.values()) else "No collections"
    
    # Calculate completion rate
    completion_rate = (completed_collections / total_collections * 100) if total_collections > 0 else 0

    return {
        "collections_by_day": collections_by_day,
        "total_collections": total_collections,
        "total_distance": round(total_distance, 2),
        "completion_rate": round(completion_rate, 2),
        "busiest_day": busiest_day
    }

@router.get("/dashboard/monthly", response_model=MonthlyStats)
async def get_monthly_stats(driver_id: int, db: Session = Depends(get_db)):
    """Get driver's statistics for the current month"""
    today = datetime.utcnow().date()
    start_of_month = today.replace(day=1)
    if today.month == 12:
        end_of_month = today.replace(year=today.year + 1, month=1, day=1)
    else:
        end_of_month = today.replace(month=today.month + 1, day=1)

    collections = db.query(WasteCollection).options(
        joinedload(WasteCollection.customer_location)
    ).filter(
        and_(
            WasteCollection.driver_id == driver_id,
            WasteCollection.scheduled_time >= start_of_month,
            WasteCollection.scheduled_time < end_of_month
        )
    ).all()

    total_collections = len(collections)
    completed_collections = sum(1 for c in collections if c.status == "COMPLETED")
    
    # Calculate total distance
    total_distance = sum(
        calculate_distance(
            5.6037, -0.1870,  # Default Accra coordinates
            c.customer_location.latitude,
            c.customer_location.longitude
        ) for c in collections if c.customer_location
    )

    # Group collections by week
    collections_by_week = {}
    for collection in collections:
        week_number = (collection.scheduled_time.date() - start_of_month).days // 7 + 1
        week_key = f"Week {week_number}"
        collections_by_week[week_key] = collections_by_week.get(week_key, 0) + 1

    # Calculate average daily collections
    days_in_month = (end_of_month - start_of_month).days
    average_daily = total_collections / days_in_month if days_in_month > 0 else 0
    
    # Calculate completion rate
    completion_rate = (completed_collections / total_collections * 100) if total_collections > 0 else 0

    return {
        "total_collections": total_collections,
        "average_daily_collections": round(average_daily, 2),
        "total_distance": round(total_distance, 2),
        "completion_rate": round(completion_rate, 2),
        "collections_by_week": collections_by_week
    }

@router.get("/dashboard", response_model=PerformanceStats)
async def get_driver_dashboard(driver_id: int, db: Session = Depends(get_db)):
    """Get comprehensive driver dashboard"""
    daily_stats = await get_today_stats(driver_id, db)
    weekly_stats = await get_weekly_stats(driver_id, db)
    monthly_stats = await get_monthly_stats(driver_id, db)

    return {
        "daily": daily_stats,
        "weekly": weekly_stats,
        "monthly": monthly_stats
    }