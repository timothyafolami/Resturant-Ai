from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from langchain_core.tools import tool
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func

from src.database import (
    get_db, 
    EmployeeTable, 
    StorageItemTable, 
    RecipeTable, 
    RecipeIngredientTable,
    DailyMenuTable, 
    DailyMenuItemTable
)
from src.logging_config import setup_logger

logger = setup_logger()


# ========================
# Employee Tools
# ========================
@tool
def query_employees(
    name_filter: Optional[str] = None,
    position_filter: Optional[str] = None,
    department_filter: Optional[str] = None,
    shift_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    min_performance: Optional[float] = None,
    limit: int = 20
) -> str:
    """Query employee information with various filters.
    
    - name_filter: Filter by first or last name (partial match)
    - position_filter: Filter by job position
    - department_filter: Filter by department 
    - shift_filter: Filter by shift type (morning, afternoon, evening, night)
    - status_filter: Filter by status (active, inactive, on_leave)
    - min_performance: Minimum performance rating
    - limit: Maximum number of results
    """
    try:
        db = get_db()
        query = db.query(EmployeeTable)
        
        if name_filter:
            query = query.filter(or_(
                EmployeeTable.first_name.ilike(f"%{name_filter}%"),
                EmployeeTable.last_name.ilike(f"%{name_filter}%")
            ))
        
        if position_filter:
            query = query.filter(EmployeeTable.position.ilike(f"%{position_filter}%"))
            
        if department_filter:
            query = query.filter(EmployeeTable.department.ilike(f"%{department_filter}%"))
            
        if shift_filter:
            query = query.filter(EmployeeTable.shift_type == shift_filter)
            
        if status_filter:
            query = query.filter(EmployeeTable.status == status_filter)
            
        if min_performance:
            query = query.filter(EmployeeTable.performance_rating >= min_performance)
        
        employees = query.order_by(EmployeeTable.first_name).limit(limit).all()
        
        if not employees:
            return "No employees found matching the criteria."
        
        result_lines = ["👥 Employee Information:"]
        for emp in employees:
            result_lines.append(
                f"• {emp.first_name} {emp.last_name} ({emp.employee_id})\n"
                f"  Position: {emp.position} | Department: {emp.department}\n"
                f"  Shift: {emp.shift_type} | Performance: {emp.performance_rating}/5.0\n"
                f"  Tenure: {emp.tenure_months} months | Status: {emp.status}\n"
                f"  Email: {emp.email} | Phone: {emp.phone}"
            )
        
        db.close()
        return "\n\n".join(result_lines)
        
    except Exception as e:
        logger.error(f"Error querying employees: {str(e)}")
        return f"❌ Error querying employees: {str(e)}"


@tool
def get_employee_performance_stats(department: Optional[str] = None) -> str:
    """Get employee performance statistics by department or overall.
    
    - department: Optional department filter
    """
    try:
        db = get_db()
        query = db.query(EmployeeTable)
        
        if department:
            query = query.filter(EmployeeTable.department.ilike(f"%{department}%"))
        
        employees = query.all()
        
        if not employees:
            return "No employees found."
        
        # Calculate statistics
        total_employees = len(employees)
        avg_performance = sum(emp.performance_rating for emp in employees) / total_employees
        avg_tenure = sum(emp.tenure_months for emp in employees) / total_employees
        
        # Performance distribution
        high_performers = len([emp for emp in employees if emp.performance_rating >= 4.0])
        low_performers = len([emp for emp in employees if emp.performance_rating < 3.0])
        
        # Department breakdown
        dept_stats = {}
        for emp in employees:
            if emp.department not in dept_stats:
                dept_stats[emp.department] = {"count": 0, "avg_rating": 0}
            dept_stats[emp.department]["count"] += 1
            
        for dept in dept_stats:
            dept_employees = [emp for emp in employees if emp.department == dept]
            dept_stats[dept]["avg_rating"] = sum(emp.performance_rating for emp in dept_employees) / len(dept_employees)
        
        result_lines = [
            "📊 Employee Performance Statistics:",
            f"Total Employees: {total_employees}",
            f"Average Performance Rating: {avg_performance:.2f}/5.0",
            f"Average Tenure: {avg_tenure:.1f} months",
            f"High Performers (4.0+): {high_performers} ({high_performers/total_employees*100:.1f}%)",
            f"Low Performers (<3.0): {low_performers} ({low_performers/total_employees*100:.1f}%)",
            "",
            "Department Breakdown:"
        ]
        
        for dept, stats in dept_stats.items():
            result_lines.append(f"• {dept}: {stats['count']} employees, avg rating {stats['avg_rating']:.2f}")
        
        db.close()
        return "\n".join(result_lines)
        
    except Exception as e:
        logger.error(f"Error getting performance stats: {str(e)}")
        return f"❌ Error getting performance stats: {str(e)}"


# ========================
# Storage/Inventory Tools
# ========================
@tool
def query_storage_inventory(
    item_name_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
    location_filter: Optional[str] = None,
    low_stock_only: bool = False,
    expired_items_only: bool = False,
    limit: int = 20
) -> str:
    """Query storage inventory with various filters.
    
    - item_name_filter: Filter by item name (partial match)
    - category_filter: Filter by category (meat, seafood, vegetables, etc.)
    - location_filter: Filter by storage location
    - low_stock_only: Show only items below minimum stock
    - expired_items_only: Show only expired items
    - limit: Maximum number of results
    """
    try:
        db = get_db()
        query = db.query(StorageItemTable)
        
        if item_name_filter:
            query = query.filter(StorageItemTable.item_name.ilike(f"%{item_name_filter}%"))
            
        if category_filter:
            query = query.filter(StorageItemTable.category.ilike(f"%{category_filter}%"))
            
        if location_filter:
            query = query.filter(StorageItemTable.storage_location.ilike(f"%{location_filter}%"))
            
        if low_stock_only:
            query = query.filter(StorageItemTable.is_low_stock == True)
            
        if expired_items_only:
            today = date.today()
            query = query.filter(and_(
                StorageItemTable.expiry_date.is_not(None),
                StorageItemTable.expiry_date <= today
            ))
        
        items = query.order_by(StorageItemTable.item_name).limit(limit).all()
        
        if not items:
            return "No storage items found matching the criteria."
        
        result_lines = ["📦 Storage Inventory:"]
        for item in items:
            stock_status = "🔴 LOW STOCK" if item.is_low_stock else "✅ OK"
            expiry_info = f" | Expires: {item.expiry_date}" if item.expiry_date else ""
            
            result_lines.append(
                f"• {item.item_name} ({item.item_id})\n"
                f"  Category: {item.category} | Location: {item.storage_location}\n"
                f"  Stock: {item.current_stock} {item.unit} | Min: {item.minimum_stock} {item.unit}\n"
                f"  Status: {stock_status} | Cost/unit: ${item.cost_per_unit}\n"
                f"  Supplier: {item.supplier}{expiry_info}"
            )
        
        db.close()
        return "\n\n".join(result_lines)
        
    except Exception as e:
        logger.error(f"Error querying storage: {str(e)}")
        return f"❌ Error querying storage: {str(e)}"


@tool
def get_low_stock_alerts() -> str:
    """Get all items that are currently below minimum stock levels."""
    try:
        db = get_db()
        low_stock_items = db.query(StorageItemTable).filter(StorageItemTable.is_low_stock == True).all()
        
        if not low_stock_items:
            return "✅ No items are currently below minimum stock levels."
        
        result_lines = [
            "🚨 LOW STOCK ALERTS:",
            f"Total items needing restock: {len(low_stock_items)}",
            ""
        ]
        
        for item in low_stock_items:
            deficit = item.minimum_stock - item.current_stock
            result_lines.append(
                f"• {item.item_name}\n"
                f"  Current: {item.current_stock} {item.unit} | Minimum: {item.minimum_stock} {item.unit}\n"
                f"  Shortage: {deficit} {item.unit} | Supplier: {item.supplier}"
            )
        
        db.close()
        return "\n\n".join(result_lines)
        
    except Exception as e:
        logger.error(f"Error getting low stock alerts: {str(e)}")
        return f"❌ Error getting low stock alerts: {str(e)}"


# ========================
# Recipe Tools
# ========================
@tool
def query_recipes(
    dish_name_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
    cuisine_filter: Optional[str] = None,
    max_prep_time: Optional[int] = None,
    difficulty_level: Optional[int] = None,
    limit: int = 20
) -> str:
    """Query recipes with various filters.
    
    - dish_name_filter: Filter by dish name (partial match)
    - category_filter: Filter by food category
    - cuisine_filter: Filter by cuisine type
    - max_prep_time: Maximum preparation time in minutes
    - difficulty_level: Exact difficulty level (1-5)
    - limit: Maximum number of results
    """
    try:
        db = get_db()
        query = db.query(RecipeTable)
        
        if dish_name_filter:
            query = query.filter(RecipeTable.dish_name.ilike(f"%{dish_name_filter}%"))
            
        if category_filter:
            query = query.filter(RecipeTable.category.ilike(f"%{category_filter}%"))
            
        if cuisine_filter:
            query = query.filter(RecipeTable.cuisine_type.ilike(f"%{cuisine_filter}%"))
            
        if max_prep_time:
            query = query.filter(RecipeTable.prep_time_minutes <= max_prep_time)
            
        if difficulty_level:
            query = query.filter(RecipeTable.difficulty_level == difficulty_level)
        
        recipes = query.order_by(RecipeTable.dish_name).limit(limit).all()
        
        if not recipes:
            return "No recipes found matching the criteria."
        
        result_lines = ["👨‍🍳 Recipe Information:"]
        for recipe in recipes:
            total_time = recipe.prep_time_minutes + recipe.cook_time_minutes
            difficulty_stars = "⭐" * recipe.difficulty_level
            
            result_lines.append(
                f"• {recipe.dish_name} ({recipe.recipe_id})\n"
                f"  Category: {recipe.category} | Cuisine: {recipe.cuisine_type}\n"
                f"  Difficulty: {difficulty_stars} ({recipe.difficulty_level}/5)\n"
                f"  Time: {recipe.prep_time_minutes}min prep + {recipe.cook_time_minutes}min cook = {total_time}min total\n"
                f"  Serves: {recipe.serving_size} | Cost/serving: ${recipe.cost_per_serving}"
            )
        
        db.close()
        return "\n\n".join(result_lines)
        
    except Exception as e:
        logger.error(f"Error querying recipes: {str(e)}")
        return f"❌ Error querying recipes: {str(e)}"


@tool
def get_recipe_details(recipe_id: str) -> str:
    """Get detailed information about a specific recipe including ingredients and instructions.
    
    - recipe_id: The unique recipe identifier
    """
    try:
        db = get_db()
        recipe = db.query(RecipeTable).filter(RecipeTable.recipe_id == recipe_id).first()
        
        if not recipe:
            return f"Recipe with ID {recipe_id} not found."
        
        # Get ingredients
        ingredients = db.query(RecipeIngredientTable).filter(
            RecipeIngredientTable.recipe_id == recipe_id
        ).all()
        
        result_lines = [
            f"🍽️ {recipe.dish_name}",
            f"Category: {recipe.category} | Cuisine: {recipe.cuisine_type}",
            f"Difficulty: {'⭐' * recipe.difficulty_level} ({recipe.difficulty_level}/5)",
            f"Prep Time: {recipe.prep_time_minutes} minutes",
            f"Cook Time: {recipe.cook_time_minutes} minutes", 
            f"Total Time: {recipe.prep_time_minutes + recipe.cook_time_minutes} minutes",
            f"Serves: {recipe.serving_size} people",
            f"Cost per serving: ${recipe.cost_per_serving}",
            ""
        ]
        
        if ingredients:
            result_lines.append("📋 Ingredients:")
            for ing in ingredients:
                timing_info = f" (add {ing.timing})" if ing.timing != "prep" else ""
                notes_info = f" - {ing.notes}" if ing.notes else ""
                result_lines.append(
                    f"• {ing.quantity} {ing.unit} {ing.ingredient_name} ({ing.percentage}%){timing_info}{notes_info}"
                )
            result_lines.append("")
        
        if recipe.instructions:
            result_lines.append("📝 Instructions:")
            for i, instruction in enumerate(recipe.instructions, 1):
                result_lines.append(f"{i}. {instruction}")
            result_lines.append("")
        
        if recipe.allergens:
            result_lines.append(f"⚠️ Allergens: {', '.join(recipe.allergens)}")
        
        db.close()
        return "\n".join(result_lines)
        
    except Exception as e:
        logger.error(f"Error getting recipe details: {str(e)}")
        return f"❌ Error getting recipe details: {str(e)}"


# ========================
# Daily Menu Tools
# ========================
@tool
def query_daily_menu(
    menu_date: Optional[str] = None,
    location: Optional[str] = None,
    category_filter: Optional[str] = None,
    price_range: Optional[str] = None,
    dietary_restrictions: Optional[str] = None
) -> str:
    """Query daily menu items with various filters.
    
    - menu_date: Date in YYYY-MM-DD format (defaults to today)
    - location: Restaurant location/branch
    - category_filter: Filter by food category
    - price_range: Price range like "10-20" for $10-$20
    - dietary_restrictions: vegetarian, vegan, gluten_free
    """
    try:
        db = get_db()
        
        # Parse date
        if menu_date:
            try:
                target_date = datetime.strptime(menu_date, "%Y-%m-%d").date()
            except ValueError:
                return "❌ Invalid date format. Please use YYYY-MM-DD."
        else:
            target_date = date.today()
        
        # Query menus for the date
        menu_query = db.query(DailyMenuTable).filter(DailyMenuTable.menu_date == target_date)
        
        if location:
            menu_query = menu_query.filter(DailyMenuTable.restaurant_location.ilike(f"%{location}%"))
        
        menus = menu_query.all()
        
        if not menus:
            return f"No menus found for date {target_date}."
        
        # Query menu items
        menu_ids = [menu.menu_id for menu in menus]
        items_query = db.query(DailyMenuItemTable).filter(DailyMenuItemTable.menu_id.in_(menu_ids))
        
        if category_filter:
            items_query = items_query.filter(DailyMenuItemTable.category.ilike(f"%{category_filter}%"))
        
        if price_range:
            try:
                min_price, max_price = map(float, price_range.split("-"))
                items_query = items_query.filter(
                    and_(DailyMenuItemTable.price >= min_price, DailyMenuItemTable.price <= max_price)
                )
            except ValueError:
                return "❌ Invalid price range format. Please use format like '10-20'."
        
        if dietary_restrictions:
            if "vegetarian" in dietary_restrictions.lower():
                items_query = items_query.filter(DailyMenuItemTable.is_vegetarian == True)
            if "vegan" in dietary_restrictions.lower():
                items_query = items_query.filter(DailyMenuItemTable.is_vegan == True)
            if "gluten_free" in dietary_restrictions.lower():
                items_query = items_query.filter(DailyMenuItemTable.is_gluten_free == True)
        
        items = items_query.order_by(DailyMenuItemTable.category, DailyMenuItemTable.dish_name).all()
        
        if not items:
            return "No menu items found matching the criteria."
        
        result_lines = [f"🍽️ Daily Menu for {target_date}:"]
        
        # Group by menu/location
        menu_items_by_location = {}
        for item in items:
            menu = next(m for m in menus if m.menu_id == item.menu_id)
            if menu.restaurant_location not in menu_items_by_location:
                menu_items_by_location[menu.restaurant_location] = []
            menu_items_by_location[menu.restaurant_location].append((menu, item))
        
        for location, location_items in menu_items_by_location.items():
            result_lines.append(f"\n📍 {location}:")
            
            menu = location_items[0][0]  # Get menu info
            if menu.chef_recommendation:
                result_lines.append(f"👨‍🍳 Chef's Recommendation: {menu.chef_recommendation}")
            
            if menu.special_offers:
                result_lines.append(f"🎯 Special Offers: {', '.join(menu.special_offers)}")
            
            result_lines.append("")
            
            # Group items by category
            items_by_category = {}
            for _, item in location_items:
                if item.category not in items_by_category:
                    items_by_category[item.category] = []
                items_by_category[item.category].append(item)
            
            for category, category_items in items_by_category.items():
                result_lines.append(f"--- {category.upper()} ---")
                for item in category_items:
                    status_emoji = {"available": "✅", "sold_out": "❌", "limited": "⚠️"}.get(item.status, "")
                    dietary_tags = []
                    if item.is_vegetarian: dietary_tags.append("🥬 Vegetarian")
                    if item.is_vegan: dietary_tags.append("🌱 Vegan") 
                    if item.is_gluten_free: dietary_tags.append("🌾 Gluten-Free")
                    spicy_info = f" 🌶️ Spice Level: {item.spicy_level}" if item.spicy_level else ""
                    
                    result_lines.append(
                        f"• {item.dish_name} - ${item.price} {status_emoji}\n"
                        f"  {item.description}\n"
                        f"  Prep time: {item.estimated_prep_time} min{spicy_info}\n"
                        f"  {' | '.join(dietary_tags)}" if dietary_tags else ""
                    )
                result_lines.append("")
        
        db.close()
        return "\n".join(result_lines)
        
    except Exception as e:
        logger.error(f"Error querying daily menu: {str(e)}")
        return f"❌ Error querying daily menu: {str(e)}"


@tool
def get_menu_item_details(dish_name: str, menu_date: Optional[str] = None) -> str:
    """Get detailed information about a specific menu item including recipe and availability.
    
    - dish_name: Name of the dish to look up
    - menu_date: Date in YYYY-MM-DD format (defaults to today)
    """
    try:
        db = get_db()
        
        # Parse date
        if menu_date:
            try:
                target_date = datetime.strptime(menu_date, "%Y-%m-%d").date()
            except ValueError:
                return "❌ Invalid date format. Please use YYYY-MM-DD."
        else:
            target_date = date.today()
        
        # Find the menu item
        menu_item = db.query(DailyMenuItemTable).join(DailyMenuTable).filter(
            and_(
                DailyMenuTable.menu_date == target_date,
                DailyMenuItemTable.dish_name.ilike(f"%{dish_name}%")
            )
        ).first()
        
        if not menu_item:
            return f"Menu item '{dish_name}' not found for date {target_date}."
        
        # Get the associated recipe
        recipe = db.query(RecipeTable).filter(RecipeTable.recipe_id == menu_item.recipe_id).first()
        
        # Get menu info
        menu = db.query(DailyMenuTable).filter(DailyMenuTable.menu_id == menu_item.menu_id).first()
        
        result_lines = [
            f"🍽️ {menu_item.dish_name}",
            f"📍 Location: {menu.restaurant_location}",
            f"💰 Price: ${menu_item.price}",
            f"📝 Description: {menu_item.description}",
            f"🕐 Estimated prep time: {menu_item.estimated_prep_time} minutes",
            f"📊 Status: {menu_item.status}",
            ""
        ]
        
        # Dietary information
        dietary_info = []
        if menu_item.is_vegetarian: dietary_info.append("🥬 Vegetarian")
        if menu_item.is_vegan: dietary_info.append("🌱 Vegan")
        if menu_item.is_gluten_free: dietary_info.append("🌾 Gluten-Free")
        if menu_item.spicy_level: dietary_info.append(f"🌶️ Spice Level: {menu_item.spicy_level}/5")
        if menu_item.calories: dietary_info.append(f"🔥 Calories: {menu_item.calories}")
        
        if dietary_info:
            result_lines.append(" | ".join(dietary_info))
            result_lines.append("")
        
        if menu_item.available_quantity:
            result_lines.append(f"📦 Limited quantity available: {menu_item.available_quantity}")
            result_lines.append("")
        
        # Recipe information
        if recipe:
            result_lines.extend([
                "👨‍🍳 Recipe Information:",
                f"Cuisine: {recipe.cuisine_type}",
                f"Difficulty: {'⭐' * recipe.difficulty_level} ({recipe.difficulty_level}/5)",
                f"Total cooking time: {recipe.prep_time_minutes + recipe.cook_time_minutes} minutes",
                f"Serves: {recipe.serving_size}",
                ""
            ])
            
            if recipe.allergens:
                result_lines.append(f"⚠️ Allergens: {', '.join(recipe.allergens)}")
        
        db.close()
        return "\n".join(result_lines)
        
    except Exception as e:
        logger.error(f"Error getting menu item details: {str(e)}")
        return f"❌ Error getting menu item details: {str(e)}"


# Combine all database tools
DATABASE_TOOLS = [
    query_employees,
    get_employee_performance_stats,
    query_storage_inventory,
    get_low_stock_alerts,
    query_recipes,
    get_recipe_details,
    query_daily_menu,
    get_menu_item_details
]
