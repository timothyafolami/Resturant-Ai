"""
Synthetic data generator for restaurant CRM system.
Generates realistic employee, recipe, storage, and menu data.
"""

import random
import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Dict, Any
from faker import Faker

from src.database import (
    SessionLocal, 
    EmployeeTable, 
    StorageItemTable, 
    RecipeTable, 
    RecipeIngredientTable,
    DailyMenuTable, 
    DailyMenuItemTable,
    create_tables
)
from src.logging_config import setup_logger

fake = Faker()
logger = setup_logger()

# Restaurant data constants
POSITIONS = [
    "Head Chef", "Sous Chef", "Line Cook", "Prep Cook", "Pastry Chef",
    "Restaurant Manager", "Assistant Manager", "Floor Manager",
    "Head Waiter", "Waiter", "Waitress", "Host/Hostess", "Busser",
    "Bartender", "Barista", "Dishwasher", "Kitchen Assistant"
]

DEPARTMENTS = ["Kitchen", "Service", "Management", "Bar", "Cleaning"]

SHIFT_TYPES = ["morning", "afternoon", "evening", "night"]

INGREDIENT_CATEGORIES = [
    "meat", "seafood", "vegetables", "fruits", "dairy", 
    "grains", "spices", "beverages", "oils", "condiments"
]

STORAGE_LOCATIONS = ["freezer", "refrigerator", "pantry", "dry_storage", "wine_cellar"]

CUISINES = [
    "Italian", "Mexican", "Chinese", "Japanese", "Thai", "Indian", 
    "French", "Mediterranean", "American", "Korean", "Vietnamese"
]

FOOD_CATEGORIES = ["Appetizer", "Main Course", "Dessert", "Beverage", "Side Dish", "Salad", "Soup"]

RESTAURANT_LOCATIONS = [
    "Downtown Main Street", "Westside Shopping Center", "Airport Terminal", 
    "Beachfront Promenade", "University District"
]

# Sample dish names by cuisine
DISHES_BY_CUISINE = {
    "Italian": [
        "Spaghetti Carbonara", "Margherita Pizza", "Chicken Parmigiana", "Risotto ai Porcini",
        "Lasagna Bolognese", "Fettuccine Alfredo", "Osso Buco", "Tiramisu", "Bruschetta"
    ],
    "Mexican": [
        "Chicken Tacos", "Beef Burrito", "Quesadilla", "Enchiladas Verdes", "Carne Asada",
        "Guacamole and Chips", "Churros", "Tres Leches Cake", "Fish Tacos"
    ],
    "Chinese": [
        "Kung Pao Chicken", "Sweet and Sour Pork", "Beef and Broccoli", "Fried Rice",
        "Hot Pot", "Dumplings", "Peking Duck", "Mapo Tofu", "Spring Rolls"
    ],
    "Japanese": [
        "Chicken Teriyaki", "Sushi Platter", "Ramen Bowl", "Tempura Vegetables",
        "Miso Soup", "Sashimi Selection", "Yakitori", "Mochi Ice Cream", "Udon Noodles"
    ],
    "American": [
        "Classic Burger", "BBQ Ribs", "Grilled Chicken Sandwich", "Caesar Salad",
        "Mac and Cheese", "Buffalo Wings", "Apple Pie", "Chocolate Brownie", "Fish and Chips"
    ]
}

# Sample ingredients by category
INGREDIENTS_BY_CATEGORY = {
    "meat": [
        "Chicken Breast", "Ground Beef", "Pork Tenderloin", "Lamb Chops", "Turkey Breast",
        "Bacon", "Ham", "Sausage", "Beef Steak", "Chicken Thighs"
    ],
    "seafood": [
        "Salmon Fillet", "Shrimp", "Cod Fish", "Tuna Steak", "Lobster Tail",
        "Crab Meat", "Mussels", "Clams", "Scallops", "Tilapia"
    ],
    "vegetables": [
        "Tomatoes", "Onions", "Bell Peppers", "Mushrooms", "Broccoli",
        "Carrots", "Spinach", "Lettuce", "Garlic", "Potatoes", "Zucchini"
    ],
    "fruits": [
        "Lemons", "Limes", "Apples", "Bananas", "Strawberries",
        "Oranges", "Avocados", "Berries", "Mangoes", "Pineapple"
    ],
    "dairy": [
        "Milk", "Heavy Cream", "Butter", "Cheddar Cheese", "Mozzarella Cheese",
        "Parmesan Cheese", "Yogurt", "Sour Cream", "Cream Cheese", "Eggs"
    ],
    "grains": [
        "White Rice", "Brown Rice", "Pasta", "Bread", "Flour",
        "Quinoa", "Oats", "Barley", "Couscous", "Noodles"
    ],
    "spices": [
        "Salt", "Black Pepper", "Garlic Powder", "Paprika", "Cumin",
        "Oregano", "Basil", "Thyme", "Rosemary", "Chili Powder"
    ],
    "oils": [
        "Olive Oil", "Vegetable Oil", "Coconut Oil", "Sesame Oil", "Canola Oil"
    ],
    "condiments": [
        "Soy Sauce", "Hot Sauce", "Ketchup", "Mustard", "Mayonnaise",
        "Vinegar", "Worcestershire Sauce", "BBQ Sauce", "Honey", "Maple Syrup"
    ]
}

COMMON_ALLERGENS = ["dairy", "eggs", "fish", "shellfish", "nuts", "peanuts", "soy", "wheat", "gluten"]

COOKING_INSTRUCTIONS = [
    "Heat oil in a large pan over medium heat",
    "Season with salt and pepper to taste",
    "Add ingredients and cook until tender",
    "Stir frequently to prevent burning",
    "Cook until internal temperature reaches safe levels",
    "Let rest for 5 minutes before serving",
    "Garnish with fresh herbs",
    "Serve immediately while hot",
    "Drain excess liquid if necessary",
    "Adjust seasoning as needed"
]


def generate_employees(count: int = 50) -> List[EmployeeTable]:
    """Generate synthetic employee data"""
    employees = []
    
    for i in range(count):
        hire_date = fake.date_between(start_date='-5y', end_date='today')
        tenure_months = (date.today() - hire_date).days // 30
        
        employee = EmployeeTable(
            employee_id=str(uuid.uuid4()),
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=fake.email(),
            phone=fake.phone_number(),
            position=random.choice(POSITIONS),
            department=random.choice(DEPARTMENTS),
            hire_date=hire_date,
            tenure_months=tenure_months,
            salary=Decimal(str(random.randint(3000, 8000))),
            performance_rating=round(random.uniform(2.0, 5.0), 1),
            shift_type=random.choice(SHIFT_TYPES),
            status=random.choice(["active", "active", "active", "on_leave", "inactive"]),  # Weighted towards active
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        employees.append(employee)
    
    return employees


def generate_storage_items(count: int = 100) -> List[StorageItemTable]:
    """Generate synthetic storage/inventory data"""
    storage_items = []
    
    for category, ingredients in INGREDIENTS_BY_CATEGORY.items():
        for ingredient in ingredients:
            current_stock = Decimal(str(random.uniform(5, 100)))
            minimum_stock = Decimal(str(random.uniform(10, 30)))
            is_low_stock = current_stock < minimum_stock
            
            # Some items have expiry dates
            expiry_date = None
            if category in ["meat", "seafood", "dairy", "fruits"]:
                expiry_date = fake.date_between(start_date='today', end_date='+30d')
            
            item = StorageItemTable(
                item_id=str(uuid.uuid4()),
                item_name=ingredient,
                category=category,
                current_stock=current_stock,
                unit=random.choice(["kg", "liters", "pieces", "pounds", "cups"]),
                minimum_stock=minimum_stock,
                maximum_stock=Decimal(str(random.uniform(100, 200))),
                cost_per_unit=Decimal(str(random.uniform(0.50, 25.00))),
                supplier=fake.company(),
                storage_location=random.choice(STORAGE_LOCATIONS),
                expiry_date=expiry_date,
                last_restocked=fake.date_between(start_date='-30d', end_date='today'),
                is_low_stock=is_low_stock,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            storage_items.append(item)
    
    return storage_items


def generate_recipes_and_ingredients(storage_items: List[StorageItemTable], count: int = 60) -> tuple:
    """Generate synthetic recipe data with ingredients"""
    recipes = []
    recipe_ingredients = []
    
    for cuisine, dishes in DISHES_BY_CUISINE.items():
        for dish in dishes:
            recipe_id = str(uuid.uuid4())
            
            # Generate recipe
            prep_time = random.randint(10, 60)
            cook_time = random.randint(15, 90)
            difficulty = random.randint(1, 5)
            serving_size = random.randint(2, 8)
            
            # Generate cooking instructions
            instructions = random.sample(COOKING_INSTRUCTIONS, random.randint(4, 8))
            
            # Generate allergens
            allergens = random.sample(COMMON_ALLERGENS, random.randint(0, 3))
            
            recipe = RecipeTable(
                recipe_id=recipe_id,
                dish_name=dish,
                category=random.choice(FOOD_CATEGORIES),
                cuisine_type=cuisine,
                difficulty_level=difficulty,
                prep_time_minutes=prep_time,
                cook_time_minutes=cook_time,
                serving_size=serving_size,
                instructions=instructions,
                allergens=allergens,
                nutritional_info={
                    "calories": random.randint(200, 800),
                    "protein": f"{random.randint(10, 50)}g",
                    "carbs": f"{random.randint(20, 100)}g",
                    "fat": f"{random.randint(5, 40)}g"
                },
                cost_per_serving=Decimal(str(random.uniform(3.00, 15.00))),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            recipes.append(recipe)
            
            # Generate recipe ingredients (3-8 ingredients per recipe)
            num_ingredients = random.randint(3, 8)
            selected_items = random.sample(storage_items, num_ingredients)
            total_percentage = 0
            
            for i, storage_item in enumerate(selected_items):
                if i == len(selected_items) - 1:  # Last ingredient gets remaining percentage
                    percentage = 100 - total_percentage
                else:
                    percentage = random.uniform(5, 30)
                    total_percentage += percentage
                
                ingredient = RecipeIngredientTable(
                    id=str(uuid.uuid4()),
                    recipe_id=recipe_id,
                    ingredient_id=storage_item.item_id,
                    ingredient_name=storage_item.item_name,
                    quantity=Decimal(str(random.uniform(0.1, 3.0))),
                    unit=storage_item.unit,
                    percentage=round(percentage, 1),
                    timing=random.choice(["prep", "start", "middle", "end", "garnish"]),
                    notes=fake.text(max_nb_chars=100) if random.random() < 0.3 else None
                )
                recipe_ingredients.append(ingredient)
    
    return recipes, recipe_ingredients


def generate_daily_menus(recipes: List[RecipeTable], days: int = 7) -> tuple:
    """Generate daily menus for multiple days and locations"""
    daily_menus = []
    daily_menu_items = []
    
    for day_offset in range(days):
        menu_date = date.today() + timedelta(days=day_offset)
        
        for location in RESTAURANT_LOCATIONS:
            menu_id = str(uuid.uuid4())
            
            # Select random recipes for this menu (15-25 items)
            selected_recipes = random.sample(recipes, random.randint(15, 25))
            
            daily_menu = DailyMenuTable(
                menu_id=menu_id,
                menu_date=menu_date,
                restaurant_location=location,
                special_offers=[
                    "Happy Hour 4-6 PM: 20% off appetizers",
                    "Chef's Special: Seasonal ingredients",
                    "Weekend Brunch: Available Saturday & Sunday"
                ] if random.random() < 0.7 else [],
                chef_recommendation=random.choice(selected_recipes).dish_name if random.random() < 0.8 else None,
                total_items=len(selected_recipes),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            daily_menus.append(daily_menu)
            
            # Generate menu items
            for recipe in selected_recipes:
                menu_item = DailyMenuItemTable(
                    menu_item_id=str(uuid.uuid4()),
                    menu_id=menu_id,
                    recipe_id=recipe.recipe_id,
                    dish_name=recipe.dish_name,
                    description=fake.text(max_nb_chars=150),
                    category=recipe.category,
                    price=Decimal(str(random.uniform(8.99, 35.99))),
                    status=random.choice(["available", "available", "available", "limited", "sold_out"]),
                    estimated_prep_time=recipe.prep_time_minutes + recipe.cook_time_minutes,
                    available_quantity=random.randint(5, 20) if random.random() < 0.3 else None,
                    spicy_level=random.randint(1, 5) if random.random() < 0.4 else None,
                    is_vegetarian=random.random() < 0.3,
                    is_vegan=random.random() < 0.15,
                    is_gluten_free=random.random() < 0.2,
                    calories=recipe.nutritional_info.get("calories") if recipe.nutritional_info else None
                )
                daily_menu_items.append(menu_item)
    
    return daily_menus, daily_menu_items


def populate_database():
    """Main function to populate the database with synthetic data"""
    logger.info("🚀 Starting database population with synthetic data...")
    
    # Create tables first
    create_tables()
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Clear existing data (for development)
        logger.info("🧹 Clearing existing data...")
        db.query(DailyMenuItemTable).delete()
        db.query(DailyMenuTable).delete()
        db.query(RecipeIngredientTable).delete()
        db.query(RecipeTable).delete()
        db.query(StorageItemTable).delete()
        db.query(EmployeeTable).delete()
        db.commit()
        
        # Generate employees
        logger.info("👥 Generating employee data...")
        employees = generate_employees(50)
        db.add_all(employees)
        db.commit()
        logger.info(f"✅ Created {len(employees)} employees")
        
        # Generate storage items
        logger.info("📦 Generating storage/inventory data...")
        storage_items = generate_storage_items()
        db.add_all(storage_items)
        db.commit()
        logger.info(f"✅ Created {len(storage_items)} storage items")
        
        # Generate recipes and ingredients
        logger.info("👨‍🍳 Generating recipes and ingredients...")
        recipes, recipe_ingredients = generate_recipes_and_ingredients(storage_items)
        db.add_all(recipes)
        db.commit()
        db.add_all(recipe_ingredients)
        db.commit()
        logger.info(f"✅ Created {len(recipes)} recipes with {len(recipe_ingredients)} ingredients")
        
        # Generate daily menus
        logger.info("🍽️ Generating daily menus...")
        daily_menus, daily_menu_items = generate_daily_menus(recipes, 7)
        db.add_all(daily_menus)
        db.commit()
        db.add_all(daily_menu_items)
        db.commit()
        logger.info(f"✅ Created {len(daily_menus)} daily menus with {len(daily_menu_items)} menu items")
        
        logger.info("🎉 Database population completed successfully!")
        
        # Print summary
        print("\n" + "="*60)
        print("📊 DATABASE POPULATION SUMMARY")
        print("="*60)
        print(f"👥 Employees: {len(employees)}")
        print(f"📦 Storage Items: {len(storage_items)}")
        print(f"👨‍🍳 Recipes: {len(recipes)}")
        print(f"🥘 Recipe Ingredients: {len(recipe_ingredients)}")
        print(f"🍽️ Daily Menus: {len(daily_menus)}")
        print(f"📋 Menu Items: {len(daily_menu_items)}")
        print("="*60)
        
    except Exception as e:
        logger.error(f"❌ Error populating database: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    populate_database()
