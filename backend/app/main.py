from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from .services.recipe_generator import generate_recipe

app = FastAPI(title="Portfolio Backtesting API", version="1.0.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RecipeRequest(BaseModel):
    stocks: List[str]
    strategy_instruction: str


class RecipeResponse(BaseModel):
    recipe: Dict[str, Any]
    equity_curve: List[Dict[str, Any]]
    summary_stats: Dict[str, Any]


@app.get("/")
def read_root():
    return {"message": "Portfolio Backtesting API", "status": "running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/api/generate-recipe", response_model=RecipeResponse)
async def generate_recipe_endpoint(request: RecipeRequest):
    """
    Generate a recipe based on selected stocks and strategy instruction.
    Currently returns mock data - to be replaced with actual implementation.
    """
    try:
        # Call the recipe generator (to be replaced with actual logic)
        result = generate_recipe(
            stocks=request.stocks,
            strategy_instruction=request.strategy_instruction
        )
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating recipe: {str(e)}")
