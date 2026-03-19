# Linux Deployment Checklist

## ✅ ALREADY LINUX-COMPATIBLE

The backend code is **already Linux-ready** with proper cross-platform practices:

### Good Practices Found:
1. **Path Handling**: Uses `pathlib.Path` throughout for cross-platform path operations
2. **No Windows-specific APIs**: No Win32 API calls or Windows-only modules
3. **Database paths**: All use `Path` objects with `/` separators
4. **File I/O**: Proper encoding specified (`encoding="utf-8"`) in file operations
5. **No shell scripts**: Pure Python implementation

## ⚠️ MINOR ISSUES (Test/Dev Code Only)

The following hardcoded Windows paths exist **only in test code** and won't affect production:

### 1. Test Scripts (Not Used in Production)
```python
# backend/app/services/recipe_interpreter/backtesting_from_json.py (line 435)
if __name__ == "__main__":
    recipe_path = r"C:\Python\recipe-interpreter\prompts\backtesting_example_expected_output.json"
```

### 2. Utility Functions (Not Called in API)
```python
# backend/app/services/price_data/data_fetch.py (line 272)
def update_price_data():
    market_json = r"C:\Python\hackathon\backend\data\market_data.json"
```

### 3. Development Scripts
```python
# backend/app/services/price_data/load_csv_to_db.py (line 12)
CSV_FOLDER = r"C:\Python\portfolio-project\data\price_data"

# backend/app/services/news_api/article.py (line 88)
data_dump = r"C:\Python\hackathon\news_dump.csv"
```

## 🔧 OPTIONAL IMPROVEMENTS

While not required for deployment, these could be improved:

### 1. Replace `os.path.join` with `pathlib.Path`
Currently these files use `os.path.join` (works on both OS but pathlib is cleaner):
- `app/services/price_data/load_csv_to_db.py` (line 13)
- `app/services/bl_stress/llm_parser.py` (lines 160, 164, 250)
- `app/services/bl_llm_parser/parser.py` (lines 167, 171, 186)

**Note**: `os.path.join` is cross-platform compatible, so this is purely cosmetic.

### 2. User-Agent String
```python
# app/services/news_api/article.py (line 19)
'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
```
**Impact**: None - this is just a browser identification string for web scraping.

## 📋 PRE-DEPLOYMENT CHECKLIST

### Environment Setup
- [ ] Python 3.9+ installed
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Set environment variables:
  - `OPENAI_API_KEY` (for LLM features)
  - `VITE_API_BASE_URL=/api` (if using custom proxy)

### Directory Structure
Ensure these directories exist (created automatically by the app):
```
backend/
  data/
    agent_audits/
    bl_recipes/
    agent_costs.db (auto-created)
    llm_usage.db (auto-created)
    admin_meta.db (auto-created)
    portfolios.db (auto-created)
    market_data.json (required - should exist)
    news.json (optional)
```

### File Permissions
- [ ] Read/write access to `backend/data/` directory
- [ ] Read access to all Python source files
- [ ] Execute permission on Python interpreter

### Network
- [ ] Port 8000 (or configured port) available for FastAPI
- [ ] Outbound HTTPS allowed (for OpenAI API, yfinance, news scraping)

### Testing on Linux
```bash
# 1. Navigate to backend directory
cd backend

# 2. Activate virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux
# venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Test the backend server
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 5. Verify health
curl http://localhost:8000/api/admin/console
```

## 🚀 DEPLOYMENT COMMANDS

### Using Uvicorn (Development)
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

### Using Gunicorn (Production)
```bash
cd backend
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UnicornWorker --bind 0.0.0.0:8000
```

### Using Docker (Recommended for Production)
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Copy requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ .

# Create data directory
RUN mkdir -p data/agent_audits data/bl_recipes

# Expose port
EXPOSE 8000

# Run with gunicorn
CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UnicornWorker", "--bind", "0.0.0.0:8000"]
```

## ✅ CONCLUSION

**The backend is fully Linux-compatible as-is.** All Windows-specific paths are limited to test code that won't run in production. The actual FastAPI application uses cross-platform pathlib and will work on Linux without any code changes.

### Action Required: **NONE** ✨

The only requirements for Linux deployment are:
1. Python 3.9+
2. Install dependencies from requirements.txt
3. Set OPENAI_API_KEY environment variable
4. Ensure data directory is writable

No code modifications are needed for Linux deployment!
