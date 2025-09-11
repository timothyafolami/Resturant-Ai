# 🍽️ Restaurant CRM Chat Applications

A comprehensive restaurant management system with AI-powered chat interfaces for both internal staff and external customers. Built with LangGraph orchestration and PostgreSQL databases.

## ✨ Features

### 🏪 Internal Staff Chat
- **Employee Management**: Query employee information, performance stats, schedules, and HR data
- **Recipe Management**: Access detailed recipes with ingredients, instructions, and nutritional info
- **Inventory Management**: Monitor food storage, stock levels, and low stock alerts
- **Menu Management**: Check daily menu items, availability, and pricing

### 🙋 Customer Chat  
- **Menu Discovery**: Browse today's menu with descriptions and prices
- **Dietary Filters**: Find vegetarian, vegan, and gluten-free options
- **Dish Details**: Get preparation times, ingredients, and allergen information
- **Recommendations**: Receive personalized dish suggestions

## 🗄️ Database Schema

The system uses four PostgreSQL databases:

1. **Employees** - Staff information, performance ratings, shifts, tenure
2. **Recipes** - Dish details, ingredients, cooking instructions, nutritional data
3. **Storage/Inventory** - Ingredient stock levels, suppliers, expiry dates
4. **Daily Menu** - Available dishes, prices, status, dietary information

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- PostgreSQL database
- Groq API key

### Installation

1. **Clone and setup environment:**
```bash
git clone <repository>
cd Ai-Track
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure environment:**
Copy `.env.example` to `.env` and fill in your values:
```bash
cp .env.example .env
```

Edit `.env`:
```
GROQ_API_KEY=your_groq_api_key_here
DATABASE_URL=postgresql://username:password@localhost:5432/restaurant_crm
```

4. **Run setup:**
```bash
python setup.py
```

5. **Start the applications:**

For internal staff:
```bash
python main_internal.py
```

For customers:
```bash
python main_external.py
```

## 🎯 Usage Examples

### Internal Staff Queries

```
🧑‍💼 Staff Query: Show me all employees in the kitchen department
🧑‍💼 Staff Query: What recipes use chicken breast?
🧑‍💼 Staff Query: Check low stock alerts
🧑‍💼 Staff Query: Get performance stats for all employees
🧑‍💼 Staff Query: What's the recipe for Spaghetti Carbonara?
```

### Customer Queries

```
🙋 Customer: What's on the menu today?
🙋 Customer: Do you have any vegan options?
🙋 Customer: Tell me about your pasta dishes
🙋 Customer: What would you recommend for someone who likes spicy food?
🙋 Customer: Show me desserts under $15
```

## 🛠️ Architecture

### LangGraph Orchestration
- **Internal Agent**: Full access to all database tools and operational data
- **External Agent**: Limited access to customer-relevant menu information
- **Tool Routing**: Automatic selection of appropriate database queries

### Database Tools
- `query_employees()` - Search and filter employee data
- `get_employee_performance_stats()` - Generate performance analytics
- `query_storage_inventory()` - Check inventory levels and stock
- `get_low_stock_alerts()` - Identify items needing restock
- `query_recipes()` - Search recipes by various criteria
- `get_recipe_details()` - Get complete recipe information
- `query_daily_menu()` - Browse menu items with filters
- `get_menu_item_details()` - Detailed dish information

### AI Prompts
- **Internal System Prompt**: Professional, data-focused for staff operations
- **External System Prompt**: Warm, customer-friendly for dining assistance
- **Context-Specific Prompts**: Low stock alerts, recommendations, dietary filters

## 📊 Sample Data

The system includes synthetic data generators that create:

- **50 Employees** across different departments and shifts
- **100+ Storage Items** with realistic stock levels and categories
- **60+ Recipes** from various cuisines with detailed ingredients
- **7 Days of Menus** across multiple restaurant locations

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GROQ_API_KEY` | Your Groq API key for LLM access | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `MODEL_NAME` | Groq model name (default: llama3-groq-70b-8192-tool-use-preview) | No |

### Database Setup

Ensure PostgreSQL is running and create a database:
```sql
CREATE DATABASE restaurant_crm;
```

The setup script will automatically create all required tables.

## 🚨 Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Verify PostgreSQL is running
   - Check DATABASE_URL format
   - Ensure database exists

2. **API Key Issues**
   - Verify GROQ_API_KEY is set correctly
   - Check API key permissions

3. **Missing Dependencies**
   - Run `pip install -r requirements.txt`
   - Ensure Python 3.8+ is being used

### Logs

The system uses structured logging. Check console output for detailed error messages and debugging information.

## 🏗️ Development

### Project Structure
```
Ai-Track/
├── src/
│   ├── agent/
│   │   └── planning.py          # LangGraph chat applications
│   ├── tools/
│   │   ├── database_tools.py    # Database query tools
│   │   └── memory_tools.py      # Memory management
│   ├── database.py              # SQLAlchemy models and setup
│   ├── models.py                # Pydantic models
│   ├── prompts.py               # System prompts and configs
│   ├── data_generator.py        # Synthetic data generation
│   └── config.py                # Environment configuration
├── main_internal.py             # Internal staff chat app
├── main_external.py             # Customer chat app
├── setup.py                     # Setup and installation script
└── requirements.txt             # Python dependencies
```

### Adding New Features

1. **New Database Tools**: Add functions to `src/tools/database_tools.py`
2. **New Prompts**: Update `src/prompts.py` with specialized prompts
3. **New Models**: Extend `src/models.py` and `src/database.py`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- Built with [LangGraph](https://github.com/langchain-ai/langgraph) for AI agent orchestration
- Uses [Groq](https://groq.com/) for fast LLM inference
- PostgreSQL for robust data storage
- Faker for realistic synthetic data generation
