# ⚡ Churn Prediction API

FastAPI backend for customer churn prediction with user authentication, dynamic dataset analysis, and retention strategies.

## ✨ Key Features

- 🔐 **User Authentication** - JWT-based registration & login
- 📤 **Dynamic Dataset Upload** - Upload CSV files for real-time ML analysis
- 📊 **Dataset Comparison** - Compare datasets over time with profit/loss analysis
- 🤖 **ML Predictions** - XGBoost model with 84.5% ROC-AUC accuracy
- 💡 **SHAP Explainability** - Understand why customers churn
- 🎯 **Retention Strategies** - Automated recommendations per customer
- 💾 **MySQL Database** - AWS RDS via MySQL Workbench for cross-environment access

## 🚀 Quick Start

```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Set environment variables (optional)
cp .env.example .env

# Run server
cd api
python main.py
# OR
uvicorn main:app --host 127.0.0.1 --port 8000
```

Server runs at: **http://localhost:8000**

## 📡 API Endpoints

### 🔐 Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Create new user account |
| POST | `/auth/login` | Login (OAuth2 form) |
| POST | `/auth/login-json` | Login (JSON body) |
| GET | `/auth/me` | Get current user info |

### 📤 Dataset Management (Protected)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/datasets/upload` | Upload & analyze CSV dataset |
| GET | `/datasets/history` | Get user's dataset history |
| GET | `/datasets/{id}` | Get specific dataset details |
| DELETE | `/datasets/{id}` | Delete a dataset |
| POST | `/datasets/compare` | Compare two datasets (profit/loss) |

### 🔮 Predictions
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/predict` | Single customer prediction |
| POST | `/predict/batch` | Batch prediction from CSV |

### 👥 Customers
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/customers` | List customers (paginated) |
| GET | `/customers/{id}` | Get customer by ID |
| GET | `/customers/search` | Search by customer ID |

### 💡 Explainability
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/explain/{id}` | SHAP-based explanation |

### 🎯 Retention
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/retention/actions` | Get all retention actions |
| GET | `/retention/customer/{id}` | Customer-specific strategy |

### 📊 Dashboard
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/dashboard/stats` | Overview KPIs |
| GET | `/dashboard/segments` | Segment distribution |
| GET | `/dashboard/risk-distribution` | Risk level breakdown |

### 📈 Model Info
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/model/metrics` | Model performance metrics |
| GET | `/model/features` | Feature importance |
| GET | `/model/comparison` | Compare all trained models |

## 📋 API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🗄️ Database Schema

### Users Table
| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| email | String | Unique email |
| username | String | Unique username |
| hashed_password | String | SHA-256 hashed password |
| full_name | String | User's full name |
| company | String | Company name |
| is_active | Boolean | Account status |
| created_at | DateTime | Registration date |

### Dataset Uploads Table
| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| user_id | Integer | Foreign key to users |
| filename | String | Original filename |
| upload_date | DateTime | Upload timestamp |
| total_customers | Integer | Customer count |
| total_revenue | Float | Sum of charges |
| churn_rate | Float | Predicted churn % |
| high_risk_count | Integer | Customers with >70% churn probability |
| revenue_at_risk | Float | Revenue from high-risk customers |
| segment_stats | JSON | Segment breakdown |

### Dataset Comparisons Table
| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| user_id | Integer | Foreign key |
| dataset_1_id | Integer | First dataset |
| dataset_2_id | Integer | Second dataset |
| customer_change | Integer | +/- customers |
| churn_rate_change | Float | Churn % change |
| revenue_change | Float | Revenue difference |
| profit_loss | Float | Estimated annual impact |
| status | String | Improved/Declined/Stable |

## 🛠️ Tech Stack

| Category | Technology |
|----------|------------|
| Framework | FastAPI |
| Auth | JWT (python-jose) |
| Database | SQLAlchemy + SQLite |
| ML | XGBoost, scikit-learn |
| Data | Pandas, NumPy |
| Validation | Pydantic |
| Server | Uvicorn |

## 📁 Project Structure

```
backend/
├── api/
│   ├── main.py              # FastAPI application
│   ├── auth_router.py       # Authentication endpoints
│   ├── dataset_router.py    # Dataset upload/compare
│   └── churn_prediction.db  # SQLite database
├── auth/
│   └── utils.py             # Password hashing, JWT tokens
├── config/
│   └── settings.py          # Environment configuration
├── database/
│   └── models.py            # SQLAlchemy models
├── data/
│   ├── loaders.py           # Data loading utilities
│   └── preprocess.py        # Preprocessing functions
├── features/
│   └── build_features.py    # Feature engineering
├── retention/
│   └── recommendations.py   # Retention strategy logic
├── utils/
│   └── logger.py            # Logging utilities
├── .env.example             # Environment template
└── requirements.txt         # Dependencies
```

## 🔧 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PROJECT_ROOT` | Auto-detected | Project root path |
| `MODELS_PATH` | `../models` | Path to ML model files |
| `DATA_PATH` | `../data/processed` | Path to data files |
| `API_HOST` | `0.0.0.0` | Server host |
| `API_PORT` | `8000` | Server port |
| `SECRET_KEY` | (generated) | JWT signing key |
| `DATABASE_URL` | (required) | MySQL AWS RDS connection |
| `ALLOWED_ORIGINS` | `*` | CORS allowed origins |

### Database Setup (AWS RDS MySQL)

1. Create AWS RDS MySQL instance
2. Connect via MySQL Workbench
3. Run `database/schema.sql` to create tables
4. Set `DATABASE_URL` in `.env`:
   ```
   DATABASE_URL=mysql+pymysql://user:pass@rds-endpoint:3306/churn_prediction
   ```

## 🔒 Authentication Flow

1. **Register**: `POST /auth/register` with email, username, password
2. **Login**: `POST /auth/login-json` returns JWT token
3. **Use API**: Include `Authorization: Bearer <token>` header
4. **Token expires**: After 24 hours (configurable)

## 📊 Dataset Upload Flow

1. User uploads CSV file via `/datasets/upload`
2. Backend validates required columns
3. ML model predicts churn for each customer
4. Results stored in database with:
   - Total customers & revenue
   - Churn rate & high-risk count
   - Revenue at risk
   - Segment breakdown
5. User can compare with previous datasets

## 🧪 Testing

```bash
# Test with Postman collection
Import: postman/Churn_Prediction_API.postman_collection.json

# Quick test
curl http://localhost:8000/
# Returns: {"status": "healthy", "message": "Customer Churn Prediction API"}
```

## 📜 License

MIT License
