# 🏀 ShotIQ - NBA Shot Prediction Platform

A machine learning-powered web application that predicts NBA shot success probability and provides comprehensive player analytics.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![React](https://img.shields.io/badge/React-18+-61DAFB.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)
![XGBoost](https://img.shields.io/badge/XGBoost-ML-orange.svg)

## 🎯 What is ShotIQ?

ShotIQ analyzes over **3.6 million NBA shots** from 18 seasons to predict the probability of any shot going in. Simply click anywhere on the interactive court, select your shot type, and get an instant ML-powered prediction.

### Features

- **🎯 Shot Predictor** - Interactive court where you click to place a shot and get probability predictions
- **📊 Player Analysis** - Deep dive into any player's shooting stats, zones, and tendencies  
- **⚔️ Head-to-Head Comparison** - Compare two players across common seasons
- **📈 Shot Charts** - Visual shot distribution with made/missed breakdowns
- **📅 Season Filtering** - Analyze specific years or career totals

## 📁 Dataset

### Source
NBA shot data from the 2004-2019 and 2023-2024 seasons (2020-2022 excluded due to data differences).

### Size
- **~3.6 million shots** across 18 seasons
- **~2,000+ unique players**

### Features Used

| Feature | Description |
|---------|-------------|
| `LOC_X` | Horizontal position on court (feet from center) |
| `LOC_Y` | Vertical position on court (feet from baseline) |
| `SHOT_DISTANCE` | Distance from the basket (feet) |
| `SHOT_TYPE` | 2PT Field Goal or 3PT Field Goal |
| `ACTION_TYPE` | Jump Shot, Layup, Dunk, Hook Shot, etc. |
| `YEAR` | Season year |

### Target Variable
- `SHOT_MADE_FLAG` - Binary (1 = made, 0 = missed)

### Data Files
```
data/
├── NBA_2004_Shots.csv
├── NBA_2005_Shots.csv
├── ...
├── NBA_2019_Shots.csv
├── NBA_2023_Shots.csv
├── NBA_2024_Shots.csv
└── nba_shots_clean.csv  # Preprocessed combined data
```

## 🤖 Model Training

### Algorithm
**XGBoost Classifier** - Chosen for its excellent performance on tabular data and ability to handle mixed feature types.

### Preprocessing Pipeline

```python
# Numeric features: passed through as-is
numeric_features = ["LOC_X", "LOC_Y", "SHOT_DISTANCE", "YEAR"]

# Categorical features: one-hot encoded
categorical_features = ["SHOT_TYPE", "ACTION_TYPE"]

preprocessor = ColumnTransformer([
    ("num", "passthrough", numeric_features),
    ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
])
```

### Model Configuration

```python
XGBClassifier(
    n_estimators=300,
    learning_rate=0.05,
    max_depth=6,
    subsample=0.8,
    colsample_bytree=0.8,
    eval_metric="logloss",
    n_jobs=-1,
)
```

### Training Process

1. Load and clean shot data from all seasons
2. Split 80/20 train/test with stratification
3. Fit preprocessing pipeline + XGBoost classifier
4. Evaluate on held-out test set

### Performance

| Metric | Score |
|--------|-------|
| Accuracy | ~61% |
| ROC-AUC | ~0.64 |

*Note: Predicting shot outcomes is inherently noisy - even the best shooters miss ~50% of their shots!*

### Retrain the Model

```bash
python scripts/retrain_model.py
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (React)                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │   Players   │  │   Predict   │  │     Compare     │  │
│  │  Analysis   │  │    Panel    │  │      View       │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                   Backend (FastAPI)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │   /api/     │  │  /api/      │  │    /api/        │  │
│  │  predict    │  │  players    │  │    compare      │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                    ML Model (XGBoost)                    │
│                   shot_model_xgb.pkl                     │
└─────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- npm or yarn

### Backend Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/nba-shot-predictor.git
cd nba-shot-predictor

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the API server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Visit `http://localhost:5173` to see the app!

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/predict_shot` | POST | Predict single shot probability |
| `/api/predict_grid` | POST | Predict probabilities for a grid of locations |
| `/api/players` | GET | Search and list players |
| `/api/player/{name}` | GET | Get player statistics |
| `/api/player/{name}/shots` | GET | Get player's shot data |
| `/api/years` | GET | Get available seasons |
| `/api/compare` | POST | Compare two players |

### Example: Predict a Shot

```bash
curl -X POST "http://localhost:8000/api/predict_shot" \
  -H "Content-Type: application/json" \
  -d '{
    "LOC_X": 0,
    "LOC_Y": 5,
    "SHOT_TYPE": "2PT Field Goal",
    "ACTION_TYPE": "Layup Shot",
    "YEAR": 2024
  }'
```

Response:
```json
{
  "probability_make": 0.52
}
```

## 🌐 Deployment

### Frontend (Vercel)
```bash
cd frontend
vercel
```

### Backend (Render)
1. Push to GitHub
2. Connect repo to Render
3. Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

See deployment configs:
- `frontend/vercel.json`
- `render.yaml`

## 📂 Project Structure

```
nba-shot-predictor/
├── app/
│   └── main.py              # FastAPI application
├── data/
│   └── NBA_*_Shots.csv      # Raw season data
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── App.tsx          # Main app
│   │   └── api.ts           # API client
│   └── vercel.json          # Vercel config
├── models/
│   └── shot_model_xgb.pkl   # Trained model
├── notebooks/
│   ├── 01_eda_multi_player.ipynb
│   └── 02_model_training.ipynb
├── scripts/
│   └── retrain_model.py     # Model retraining script
├── src/
│   ├── data_loader.py       # Data loading utilities
│   ├── features.py          # Feature engineering
│   ├── inference.py         # Model inference
│   └── viz.py               # Visualization helpers
├── requirements.txt
└── README.md
```

## 🛠️ Tech Stack

**Backend:**
- Python 3.11
- FastAPI
- XGBoost
- scikit-learn
- pandas / numpy

**Frontend:**
- React 18
- TypeScript
- Vite
- CSS (custom design system)

**Deployment:**
- Vercel (frontend)
- Render (backend)

## 📊 Key Insights from the Data

- **Layups** have the highest success rate (~52%) but are often contested
- **Corner 3s** are the most efficient 3-point shots
- Shot success drops significantly beyond 15 feet
- **Dunks** have the highest make percentage (~80%+)
- The **restricted area** (within 4ft of rim) sees the highest volume of shots

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is for educational purposes. NBA data is property of the NBA.

---

