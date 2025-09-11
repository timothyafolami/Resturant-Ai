from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, date, time
from decimal import Decimal
from enum import Enum


# ========================
# Employee Information
# ========================
class ShiftType(str, Enum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    NIGHT = "night"


class EmployeeStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ON_LEAVE = "on_leave"


class Employee(BaseModel):
    """Employee information"""
    employee_id: str = Field(..., description="Unique employee identifier")
    first_name: str = Field(..., description="Employee first name")
    last_name: str = Field(..., description="Employee last name")
    email: str = Field(..., description="Employee email address")
    phone: str = Field(..., description="Employee phone number")
    position: str = Field(..., description="Job position (e.g., chef, waiter, manager)")
    department: str = Field(..., description="Department (kitchen, service, management)")
    hire_date: date = Field(..., description="Date when employee was hired")
    tenure_months: int = Field(..., description="Tenure in months")
    salary: Decimal = Field(..., description="Monthly salary")
    performance_rating: float = Field(..., description="Performance rating (1.0-5.0)")
    shift_type: ShiftType = Field(..., description="Primary shift type")
    status: EmployeeStatus = Field(default=EmployeeStatus.ACTIVE, description="Employee status")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ========================
# Recipe
# ========================
class IngredientTiming(str, Enum):
    PREP = "prep"
    START = "start"
    MIDDLE = "middle"
    END = "end"
    GARNISH = "garnish"


class RecipeIngredient(BaseModel):
    """Individual ingredient in a recipe"""
    ingredient_id: str = Field(..., description="Reference to storage ingredient")
    ingredient_name: str = Field(..., description="Name of the ingredient")
    quantity: Decimal = Field(..., description="Amount needed")
    unit: str = Field(..., description="Unit of measurement (kg, liters, pieces)")
    percentage: float = Field(..., description="Percentage of total recipe (0-100)")
    timing: IngredientTiming = Field(..., description="When to add ingredient")
    notes: Optional[str] = Field(None, description="Special preparation notes")


class Recipe(BaseModel):
    """Recipe information"""
    recipe_id: str = Field(..., description="Unique recipe identifier")
    dish_name: str = Field(..., description="Name of the dish")
    category: str = Field(..., description="Food category (appetizer, main, dessert)")
    cuisine_type: str = Field(..., description="Cuisine type (italian, chinese, etc.)")
    difficulty_level: int = Field(..., description="Difficulty level (1-5)")
    prep_time_minutes: int = Field(..., description="Preparation time in minutes")
    cook_time_minutes: int = Field(..., description="Cooking time in minutes")
    serving_size: int = Field(..., description="Number of servings")
    ingredients: List[RecipeIngredient] = Field(..., description="List of ingredients")
    instructions: List[str] = Field(..., description="Step-by-step cooking instructions")
    allergens: List[str] = Field(default_factory=list, description="List of allergens")
    nutritional_info: Optional[Dict[str, Any]] = Field(None, description="Nutritional information")
    cost_per_serving: Decimal = Field(..., description="Estimated cost per serving")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ========================
# Food Storage/Inventory
# ========================
class StorageLocation(str, Enum):
    FREEZER = "freezer"
    REFRIGERATOR = "refrigerator"
    PANTRY = "pantry"
    DRY_STORAGE = "dry_storage"
    WINE_CELLAR = "wine_cellar"


class IngredientCategory(str, Enum):
    MEAT = "meat"
    SEAFOOD = "seafood"
    VEGETABLES = "vegetables"
    FRUITS = "fruits"
    DAIRY = "dairy"
    GRAINS = "grains"
    SPICES = "spices"
    BEVERAGES = "beverages"
    OILS = "oils"
    CONDIMENTS = "condiments"


class StorageItem(BaseModel):
    """Food storage/inventory item"""
    item_id: str = Field(..., description="Unique storage item identifier")
    item_name: str = Field(..., description="Name of the ingredient/item")
    category: IngredientCategory = Field(..., description="Category of ingredient")
    current_stock: Decimal = Field(..., description="Current quantity in stock")
    unit: str = Field(..., description="Unit of measurement")
    minimum_stock: Decimal = Field(..., description="Minimum stock level (reorder point)")
    maximum_stock: Decimal = Field(..., description="Maximum stock capacity")
    cost_per_unit: Decimal = Field(..., description="Cost per unit")
    supplier: str = Field(..., description="Primary supplier name")
    storage_location: StorageLocation = Field(..., description="Where item is stored")
    expiry_date: Optional[date] = Field(None, description="Expiry date if applicable")
    last_restocked: date = Field(..., description="Last restock date")
    is_low_stock: bool = Field(default=False, description="True if below minimum stock")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ========================
# Daily Menu
# ========================
class MenuItemStatus(str, Enum):
    AVAILABLE = "available"
    SOLD_OUT = "sold_out"
    LIMITED = "limited"
    DISCONTINUED = "discontinued"


class DailyMenuItem(BaseModel):
    """Single item on daily menu"""
    menu_item_id: str = Field(..., description="Unique menu item identifier")
    recipe_id: str = Field(..., description="Reference to recipe")
    dish_name: str = Field(..., description="Name of the dish")
    description: str = Field(..., description="Description for customers")
    category: str = Field(..., description="Menu category")
    price: Decimal = Field(..., description="Price for customers")
    status: MenuItemStatus = Field(default=MenuItemStatus.AVAILABLE)
    estimated_prep_time: int = Field(..., description="Estimated preparation time in minutes")
    available_quantity: Optional[int] = Field(None, description="Limited quantity if applicable")
    spicy_level: Optional[int] = Field(None, description="Spice level (1-5)")
    is_vegetarian: bool = Field(default=False)
    is_vegan: bool = Field(default=False)
    is_gluten_free: bool = Field(default=False)
    calories: Optional[int] = Field(None, description="Calorie count")


class DailyMenu(BaseModel):
    """Daily menu"""
    menu_id: str = Field(..., description="Unique daily menu identifier")
    menu_date: date = Field(..., description="Date for this menu")
    restaurant_location: str = Field(..., description="Restaurant location/branch")
    menu_items: List[DailyMenuItem] = Field(..., description="List of available items")
    special_offers: List[str] = Field(default_factory=list, description="Special offers/promotions")
    chef_recommendation: Optional[str] = Field(None, description="Chef's recommendation")
    total_items: int = Field(..., description="Total number of menu items")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)