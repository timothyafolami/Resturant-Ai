import os
from typing import cast
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Date, Boolean, DECIMAL, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from dotenv import load_dotenv

from src.utils.logging import setup_logger

load_dotenv()
logger = setup_logger()

# Database configuration (prefer psycopg3 driver)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://user:password@localhost:5432/restaurant_crm")

# Normalize DSN to psycopg3 if a generic postgresql scheme is provided
if DATABASE_URL.startswith("postgresql://") and "+psycopg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        return db
    finally:
        pass  # Session will be closed by caller


# ========================
# Employee Tables
# ========================
class EmployeeTable(Base):
    __tablename__ = "employees"

    employee_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(50), nullable=False)
    position = Column(String(100), nullable=False)
    department = Column(String(100), nullable=False)
    hire_date = Column(Date, nullable=False)
    tenure_months = Column(Integer, nullable=False)
    salary = Column(DECIMAL(10, 2), nullable=False)
    performance_rating = Column(Float, nullable=False)
    shift_type = Column(String(20), nullable=False)  # morning, afternoon, evening, night
    status = Column(String(20), nullable=False, default="active")  # active, inactive, on_leave
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ========================
# Storage/Inventory Tables
# ========================
class StorageItemTable(Base):
    __tablename__ = "storage_items"

    item_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    item_name = Column(String(200), nullable=False)
    category = Column(String(50), nullable=False)  # meat, seafood, vegetables, etc.
    current_stock = Column(DECIMAL(10, 3), nullable=False)
    unit = Column(String(20), nullable=False)
    minimum_stock = Column(DECIMAL(10, 3), nullable=False)
    maximum_stock = Column(DECIMAL(10, 3), nullable=False)
    cost_per_unit = Column(DECIMAL(10, 2), nullable=False)
    supplier = Column(String(200), nullable=False)
    storage_location = Column(String(50), nullable=False)  # freezer, refrigerator, pantry, etc.
    expiry_date = Column(Date, nullable=True)
    last_restocked = Column(Date, nullable=False)
    is_low_stock = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ========================
# Recipe Tables
# ========================
class RecipeTable(Base):
    __tablename__ = "recipes"

    recipe_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    dish_name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)
    cuisine_type = Column(String(100), nullable=False)
    difficulty_level = Column(Integer, nullable=False)
    prep_time_minutes = Column(Integer, nullable=False)
    cook_time_minutes = Column(Integer, nullable=False)
    serving_size = Column(Integer, nullable=False)
    instructions = Column(JSON, nullable=False)  # List of instruction steps
    allergens = Column(JSON, nullable=True)  # List of allergens
    nutritional_info = Column(JSON, nullable=True)
    cost_per_serving = Column(DECIMAL(10, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to ingredients
    ingredients = relationship("RecipeIngredientTable", back_populates="recipe")


class RecipeIngredientTable(Base):
    __tablename__ = "recipe_ingredients"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    recipe_id = Column(String, ForeignKey("recipes.recipe_id"), nullable=False)
    ingredient_id = Column(String, ForeignKey("storage_items.item_id"), nullable=False)
    ingredient_name = Column(String(200), nullable=False)
    quantity = Column(DECIMAL(10, 3), nullable=False)
    unit = Column(String(20), nullable=False)
    percentage = Column(Float, nullable=False)
    timing = Column(String(20), nullable=False)  # prep, start, middle, end, garnish
    notes = Column(Text, nullable=True)

    # Relationships
    recipe = relationship("RecipeTable", back_populates="ingredients")
    storage_item = relationship("StorageItemTable")


# ========================
# Daily Menu Tables
# ========================
class DailyMenuTable(Base):
    __tablename__ = "daily_menus"

    menu_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    menu_date = Column(Date, nullable=False)
    restaurant_location = Column(String(200), nullable=False)
    special_offers = Column(JSON, nullable=True)  # List of special offers
    chef_recommendation = Column(String(500), nullable=True)
    total_items = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to menu items
    menu_items = relationship("DailyMenuItemTable", back_populates="daily_menu")


class DailyMenuItemTable(Base):
    __tablename__ = "daily_menu_items"

    menu_item_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    menu_id = Column(String, ForeignKey("daily_menus.menu_id"), nullable=False)
    recipe_id = Column(String, ForeignKey("recipes.recipe_id"), nullable=False)
    dish_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=False)
    price = Column(DECIMAL(10, 2), nullable=False)
    status = Column(String(20), nullable=False, default="available")  # available, sold_out, limited, discontinued
    estimated_prep_time = Column(Integer, nullable=False)
    available_quantity = Column(Integer, nullable=True)
    spicy_level = Column(Integer, nullable=True)
    is_vegetarian = Column(Boolean, default=False)
    is_vegan = Column(Boolean, default=False)
    is_gluten_free = Column(Boolean, default=False)
    calories = Column(Integer, nullable=True)

    # Relationships
    daily_menu = relationship("DailyMenuTable", back_populates="menu_items")
    recipe = relationship("RecipeTable")


def create_tables():
    """Create all database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully")
    except Exception as e:
        logger.error(f"❌ Error creating database tables: {str(e)}")
        raise


def drop_tables():
    """Drop all database tables (for development/testing)"""
    try:
        Base.metadata.drop_all(bind=engine)
        logger.info("✅ Database tables dropped successfully")
    except Exception as e:
        logger.error(f"❌ Error dropping database tables: {str(e)}")
        raise


if __name__ == "__main__":
    create_tables()
