from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum 
from .database import Base
import logging

# Create a logger
logger = logging.getLogger(__name__)

class RouteStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"

class CollectionStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"

class Driver(Base):
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True)
    name = Column(String, index=True)
    phone = Column(String, unique=True)
    email = Column(String, unique=True)
    password = Column(String)
    is_active = Column(Boolean, default=True)
    current_lat = Column(Float, nullable=True)
    current_lng = Column(Float, nullable=True)
    last_update = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    collections = relationship("WasteCollection", back_populates="driver")
    routes = relationship("Route", back_populates="driver")

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class WasteCollection(Base):
    __tablename__ = "waste_collections"
    
    id = Column(Integer, primary_key=True)
    driver_id = Column(Integer, ForeignKey('drivers.id'))
    location_name = Column(String, index=True)
    address = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    scheduled_time = Column(DateTime)
    actual_collection_time = Column(DateTime, nullable=True)
    status = Column(String, default="PENDING")
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_update = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    route_id=Column(Integer, ForeignKey('routes.id'), nullable=True)
    customer_location_id=Column (Integer, ForeignKey('customer_locations.id'), nullable=True)
   
    # Relationship with Driver
    driver = relationship("Driver", back_populates="collections")
    photos = relationship("CollectionPhoto", back_populates="collection")
    route = relationship("Route", back_populates="collections")
    customer_location = relationship("CustomerLocation", back_populates="collections")

    

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class CollectionPhoto(Base):
        __tablename__ = "collection_photos"

        id= Column(Integer , primary_key=True)
        collection_id = Column(Integer, ForeignKey('waste_collections.id'))
        photo_url = Column(String, nullable=False)
        photo_type= Column(String, nullable=False)
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

        #Relationship with WasteCollection
        collection = relationship("WasteCollection", back_populates="photos")


class CustomerLocation(Base):
        __tablename__ = "customer_locations"
        
        id = Column(Integer,primary_key=True)
        name = Column(String, index=True)
        address = Column(String)
        latitude = Column(Float)
        longitude = Column(Float)
        contact_name=Column(String)
        contact_number=Column(String)
        collection_frequency=Column(String)
        is_active = Column(Boolean, default=True)
        notes = Column(String, nullable=True)
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

        #Relationship with WasteCollection
        collections = relationship("WasteCollection", back_populates="customer_location")


class Route(Base):
        __tablename__ = "routes"
        
        id = Column(Integer,primary_key=True)
        driver_id = Column(Integer, ForeignKey('drivers.id'))
        date = Column(DateTime, index=True)
        start_time = Column(String)
        status=Column(String, default="PENDING")
        end_time = Column(String)
        distance = Column(Float)

        
        
        driver = relationship("Driver", back_populates="routes")
        collections = relationship("WasteCollection", back_populates="route")