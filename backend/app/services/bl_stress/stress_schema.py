"""
Stress Testing Schema Definitions

Pydantic models for structured stress test specifications.
"""

from typing import Literal, Optional
from pydantic import BaseModel, field_validator, model_validator


class StressSpec(BaseModel):
    """
    Structured specification for a Black-Litterman stress test.
    
    This model validates that required fields are present based on the
    selected stress_type and ensures no invalid combinations are specified.
    
    Attributes:
        stress_type: Type of stress test to perform
        target_label: Label of the view to stress (for view-specific tests)
        factor: Factor name to stress (for factor-specific tests)
        grid_level: Intensity level for grid generation
        template_name: Name of regime template to apply
        mode: How to apply stress (relative to base or absolute)
        magnitude_grid_level: Grid level for view magnitude in joint tests
        confidence_grid_level: Grid level for confidence in joint tests
    """
    
    stress_type: Literal[
        "view_magnitude",
        "confidence_scale",
        "factor_amplification",
        "tau_shift",
        "volatility_multiplier",
        "regime_template",
        "view_joint"
    ]
    
    target_label: Optional[str] = None
    factor: Optional[str] = None
    grid_level: Optional[Literal["conservative", "standard", "aggressive"]] = None
    template_name: Optional[str] = None
    mode: Optional[Literal["relative_to_base", "absolute"]] = None
    magnitude_grid_level: Optional[str] = None
    confidence_grid_level: Optional[str] = None
    
    @model_validator(mode='after')
    def validate_required_fields(self):
        """
        Validate that required fields are present based on stress_type.
        
        Raises:
            ValueError: If required fields are missing for the specified stress_type
        """
        st = self.stress_type
        
        # view_magnitude requires target_label
        if st == "view_magnitude":
            if not self.target_label:
                raise ValueError(
                    "stress_type 'view_magnitude' requires 'target_label' field"
                )
        
        # factor_amplification requires factor
        if st == "factor_amplification":
            if not self.factor:
                raise ValueError(
                    "stress_type 'factor_amplification' requires 'factor' field"
                )
        
        # regime_template requires template_name
        if st == "regime_template":
            if not self.template_name:
                raise ValueError(
                    "stress_type 'regime_template' requires 'template_name' field"
                )
        
        # view_joint requires both magnitude_grid_level and confidence_grid_level
        if st == "view_joint":
            if not self.magnitude_grid_level or not self.confidence_grid_level:
                raise ValueError(
                    "stress_type 'view_joint' requires both 'magnitude_grid_level' "
                    "and 'confidence_grid_level' fields"
                )
        
        return self
    
    @field_validator('grid_level', 'magnitude_grid_level', 'confidence_grid_level')
    @classmethod
    def validate_grid_level(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate grid level values are from allowed set.
        
        Args:
            v: Grid level value to validate
            
        Returns:
            Validated grid level value
            
        Raises:
            ValueError: If grid level is not in allowed values
        """
        if v is not None and v not in ["conservative", "standard", "aggressive"]:
            raise ValueError(
                f"Grid level must be one of: conservative, standard, aggressive. Got: {v}"
            )
        return v
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "stress_type": "view_magnitude",
                    "target_label": "AAPL outperforms MSFT",
                    "grid_level": "standard",
                    "mode": "relative_to_base"
                },
                {
                    "stress_type": "factor_amplification",
                    "factor": "Momentum",
                    "grid_level": "aggressive"
                },
                {
                    "stress_type": "regime_template",
                    "template_name": "high_uncertainty"
                },
                {
                    "stress_type": "view_joint",
                    "target_label": "Tech outperforms Energy",
                    "magnitude_grid_level": "standard",
                    "confidence_grid_level": "conservative"
                }
            ]
        }
    }
