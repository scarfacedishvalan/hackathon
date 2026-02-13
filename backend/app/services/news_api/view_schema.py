"""
Pydantic models for Black-Litterman view validation.

This module defines the strict schema for investor views extracted from articles.
No inference or computation happens here - only structural validation.
"""

from pydantic import BaseModel, Field, field_validator, RootModel
from typing import List, Optional


class View(BaseModel):
    """
    A single Black-Litterman view extracted from an article.
    
    Attributes:
        type: View type - "absolute", "relative", or "factor"
        asset_long: The asset expected to perform better (or the primary asset for absolute views)
        asset_short: The asset expected to underperform (only for relative views)
        factor: The market factor (e.g., "rates", "inflation") for factor views
        direction: "positive" or "negative"
        confidence: "low", "medium", or "high"
        source: The article source (e.g., "CNBC", "Bloomberg")
    """
    
    type: str = Field(..., description="View type: absolute, relative, or factor")
    asset_long: Optional[str] = Field(None, description="Primary or outperforming asset")
    asset_short: Optional[str] = Field(None, description="Underperforming asset (relative views only)")
    factor: Optional[str] = Field(None, description="Market factor (factor views only)")
    direction: str = Field(..., description="positive or negative")
    confidence: str = Field(..., description="low, medium, or high")
    source: str = Field(..., description="Article source")
    
    class Config:
        extra = "forbid"  # Strict: no extra fields allowed
    
    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate view type is one of the allowed values."""
        allowed = {"absolute", "relative", "factor"}
        if v not in allowed:
            raise ValueError(f"type must be one of {allowed}, got: {v}")
        return v
    
    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v: str) -> str:
        """Validate direction is positive or negative."""
        allowed = {"positive", "negative"}
        if v not in allowed:
            raise ValueError(f"direction must be one of {allowed}, got: {v}")
        return v
    
    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: str) -> str:
        """Validate confidence level."""
        allowed = {"low", "medium", "high"}
        if v not in allowed:
            raise ValueError(f"confidence must be one of {allowed}, got: {v}")
        return v


class ViewList(RootModel):
    """
    A collection of views extracted from an article.
    
    This root model validates that the LLM output is a proper list of views.
    """
    
    root: List[View] = Field(..., description="List of extracted views")
    
    def __iter__(self):
        """Allow iteration over views."""
        return iter(self.root)
    
    def __getitem__(self, item):
        """Allow indexing into views."""
        return self.root[item]
    
    def to_list(self) -> List[dict]:
        """Convert to list of dictionaries."""
        return [view.model_dump() for view in self.root]
