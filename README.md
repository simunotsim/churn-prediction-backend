# ⚡ Churn Prediction API

FastAPI backend for customer churn prediction, explainability, and retention strategies.

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r api/requirements.txt

# Run server
cd api
uvicorn main:app --reload --port 8000
```

## 📡 API Endpoints

### Health Check
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API health status |
| GET | `/health` | Detailed health check |

### Predictions
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/predict` | Single customer prediction |
| POST | `/predict/batch` | Batch prediction from CSV |

### Customers
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/customers` | List customers (paginated) |
| GET | `/customers/{id}` | Get customer by ID |

### Explainability
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/explain/{id}` | SHAP-based explanation |

### Retention
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/retention/actions` | Get retention actions |
| GET | `/retention/customer/{id}` | Customer retention strategy |

### Dashboard
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/dashboard/stats` | Overview KPIs |
| GET | `/dashboard/segments` | Segment distribution |
| GET | `/dashboard/risk-distribution` | Risk level breakdown |

### Model
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/model/metrics` | Model performance |
| GET | `/model/features` | Feature importance |

## 📋 API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🛠️ Tech Stack

- FastAPI
- Pydantic
- Uvicorn
- Pandas
- scikit-learn
- XGBoost
- Joblib

## 📁 Project Structure

```
backend/
├── api/
│   ├── main.py          # FastAPI application
│   └── requirements.txt # Dependencies
├── config/
│   └── settings.py      # Configuration
├── data/
│   ├── loaders.py       # Data loading utilities
│   └── preprocess.py    # Preprocessing
├── models/
│   ├── train.py         # Model training
│   ├── predict.py       # Prediction logic
│   └── evaluation.py    # Model evaluation
├── features/
│   └── build_features.py
├── retention/
│   └── recommendations.py
└── utils/
    └── logger.py
```

## 🔧 Environment Variables

Create a `.env` file:
```env
MODEL_PATH=../models
DATA_PATH=../data/processed
DEBUG=true
```

## 📜 License

MIT License
