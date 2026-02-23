"""
Scenario Models for Black-Litterman Stress Testing

Pydantic models representing concrete numeric stress scenarios.
These models contain fully resolved numeric parameters ready for backtest execution.

Unlike StressSpec (which contains symbolic instructions like "standard grid"),
scenario models contain actual values like {"new_value": -0.06}.
"""

from typing import Dict, Union, Literal, Any
from pydantic import BaseModel, field_validator, Field


class Scenario(BaseModel):
    """
    Base scenario model representing a single concrete stress test configuration.
    
    Each scenario is one point in the stress test grid. For example, if a
    StressSpec requests a "standard" view magnitude grid with 5 points,
    it generates 5 Scenario objects, each with a specific numeric value.
    
    Attributes:
        scenario_id: Unique identifier for this scenario (e.g., "mag_-2x", "conf_0.4")
        stress_type: Type of stress being applied (matches StressSpec.stress_type)
        parameters: Dictionary of concrete numeric/string parameters for this scenario
    """
    
    scenario_id: str = Field(
        ...,
        description="Unique identifier for this scenario within the stress test"
    )
    
    stress_type: Literal[
        "view_magnitude",
        "confidence_scale",
        "factor_amplification",
        "tau_shift",
        "volatility_multiplier",
        "regime_template",
        "view_joint"
    ] = Field(
        ...,
        description="Type of stress test being applied"
    )
    
    parameters: Dict[str, Union[float, str, int]] = Field(
        ...,
        description="Concrete numeric parameters for this scenario"
    )
    
    @field_validator('scenario_id')
    @classmethod
    def validate_scenario_id(cls, v: str) -> str:
        """
        Validate that scenario_id is non-empty and reasonably formatted.
        
        Args:
            v: Scenario ID to validate
            
        Returns:
            Validated scenario ID
            
        Raises:
            ValueError: If scenario_id is empty or invalid
        """
        if not v or not v.strip():
            raise ValueError("scenario_id must be non-empty")
        
        if len(v) > 100:
            raise ValueError("scenario_id must be 100 characters or less")
        
        return v.strip()
    
    @field_validator('parameters')
    @classmethod
    def validate_parameters_not_empty(cls, v: Dict) -> Dict:
        """
        Validate that parameters dictionary is not empty.
        
        Args:
            v: Parameters dictionary to validate
            
        Returns:
            Validated parameters dictionary
            
        Raises:
            ValueError: If parameters is empty
        """
        if not v:
            raise ValueError("parameters must contain at least one entry")
        
        return v
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "scenario_id": "mag_-2x",
                    "stress_type": "view_magnitude",
                    "parameters": {
                        "target_label": "AAPL outperforms MSFT",
                        "multiplier": -2.0,
                        "base_value": 0.03,
                        "new_value": -0.06
                    }
                },
                {
                    "scenario_id": "conf_0.6",
                    "stress_type": "confidence_scale",
                    "parameters": {
                        "scale_factor": 0.6
                    }
                }
            ]
        }
    }


class ViewMagnitudeScenario(BaseModel):
    """
    Scenario for stressing a specific view's magnitude.
    
    This scenario modifies the expected outperformance or expected return
    of a single view while keeping all other parameters constant.
    
    Attributes:
        scenario_id: Unique identifier (e.g., "mag_-2x", "mag_+1x")
        stress_type: Always "view_magnitude"
        target_label: Label of the view being stressed
        multiplier: Numeric multiplier applied to base value
        base_value: Original view value from recipe
        new_value: Stressed view value (base_value * multiplier)
        mode: Whether multiplier is relative or absolute
    """
    
    scenario_id: str = Field(
        ...,
        description="Unique scenario identifier"
    )
    
    stress_type: Literal["view_magnitude"] = Field(
        default="view_magnitude",
        description="Type of stress (always view_magnitude)"
    )
    
    target_label: str = Field(
        ...,
        description="Label of the view being stressed"
    )
    
    multiplier: float = Field(
        ...,
        description="Multiplier applied to the base view value"
    )
    
    base_value: float = Field(
        ...,
        description="Original expected outperformance/return from recipe"
    )
    
    new_value: float = Field(
        ...,
        description="Stressed view value after applying multiplier"
    )
    
    mode: str = Field(
        default="relative_to_base",
        description="How the multiplier is applied (relative_to_base or absolute)"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "scenario_id": "mag_-2x",
                    "stress_type": "view_magnitude",
                    "target_label": "AAPL outperforms MSFT",
                    "multiplier": -2.0,
                    "base_value": 0.02,
                    "new_value": -0.04,
                    "mode": "relative_to_base"
                }
            ]
        }
    }


class ConfidenceScenario(BaseModel):
    """
    Scenario for scaling view confidence levels.
    
    This scenario applies a uniform scaling factor to all view confidence
    values in the recipe.
    
    Attributes:
        scenario_id: Unique identifier (e.g., "conf_0.4", "conf_1.0")
        stress_type: Always "confidence_scale"
        scale_factor: Factor by which to multiply all confidences
        description: Human-readable description of the scenario
    """
    
    scenario_id: str = Field(
        ...,
        description="Unique scenario identifier"
    )
    
    stress_type: Literal["confidence_scale"] = Field(
        default="confidence_scale",
        description="Type of stress (always confidence_scale)"
    )
    
    scale_factor: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Factor to multiply all confidence values by"
    )
    
    description: str = Field(
        default="",
        description="Human-readable description of this confidence scenario"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "scenario_id": "conf_0.6",
                    "stress_type": "confidence_scale",
                    "scale_factor": 0.6,
                    "description": "60% of base confidence"
                }
            ]
        }
    }


class FactorShockScenario(BaseModel):
    """
    Scenario for amplifying or dampening a specific factor's influence.
    
    This scenario scales the loadings or exposures of a specific factor
    in the factor model, simulating increased or decreased factor importance.
    
    Attributes:
        scenario_id: Unique identifier (e.g., "factor_mom_2.0x")
        stress_type: Always "factor_amplification"
        factor: Name of the factor being stressed
        scale_factor: Multiplier for factor loadings
        description: Human-readable description
    """
    
    scenario_id: str = Field(
        ...,
        description="Unique scenario identifier"
    )
    
    stress_type: Literal["factor_amplification"] = Field(
        default="factor_amplification",
        description="Type of stress (always factor_amplification)"
    )
    
    factor: str = Field(
        ...,
        description="Name of the factor being amplified or dampened"
    )
    
    scale_factor: float = Field(
        ...,
        gt=0.0,
        description="Multiplier for factor loadings (>1 amplifies, <1 dampens)"
    )
    
    description: str = Field(
        default="",
        description="Human-readable description of the factor shock"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "scenario_id": "factor_mom_2.0x",
                    "stress_type": "factor_amplification",
                    "factor": "Momentum",
                    "scale_factor": 2.0,
                    "description": "Momentum factor amplified 2x"
                }
            ]
        }
    }


class TauShiftScenario(BaseModel):
    """
    Scenario for varying the tau parameter (prior uncertainty).
    
    Tau controls the balance between prior market equilibrium and investor views.
    Higher tau gives more weight to views, lower tau gives more weight to prior.
    
    Attributes:
        scenario_id: Unique identifier (e.g., "tau_2.0x")
        stress_type: Always "tau_shift"
        tau_multiplier: Multiplier for the base tau value
        base_tau: Original tau value from recipe
        new_tau: Stressed tau value
    """
    
    scenario_id: str = Field(
        ...,
        description="Unique scenario identifier"
    )
    
    stress_type: Literal["tau_shift"] = Field(
        default="tau_shift",
        description="Type of stress (always tau_shift)"
    )
    
    tau_multiplier: float = Field(
        ...,
        gt=0.0,
        description="Multiplier for tau parameter"
    )
    
    base_tau: float = Field(
        ...,
        gt=0.0,
        description="Original tau value from recipe"
    )
    
    new_tau: float = Field(
        ...,
        gt=0.0,
        description="Stressed tau value"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "scenario_id": "tau_2.0x",
                    "stress_type": "tau_shift",
                    "tau_multiplier": 2.0,
                    "base_tau": 0.05,
                    "new_tau": 0.10
                }
            ]
        }
    }


class VolatilityScenario(BaseModel):
    """
    Scenario for scaling market volatility (covariance matrix).
    
    This scenario uniformly scales the covariance matrix to simulate
    different volatility regimes (calm vs turbulent markets).
    
    Attributes:
        scenario_id: Unique identifier (e.g., "vol_1.5x")
        stress_type: Always "volatility_multiplier"
        volatility_multiplier: Factor to scale covariance matrix
        description: Human-readable description
    """
    
    scenario_id: str = Field(
        ...,
        description="Unique scenario identifier"
    )
    
    stress_type: Literal["volatility_multiplier"] = Field(
        default="volatility_multiplier",
        description="Type of stress (always volatility_multiplier)"
    )
    
    volatility_multiplier: float = Field(
        ...,
        gt=0.0,
        description="Multiplier for covariance matrix (>1 increases vol, <1 decreases)"
    )
    
    description: str = Field(
        default="",
        description="Human-readable description of the volatility regime"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "scenario_id": "vol_1.5x",
                    "stress_type": "volatility_multiplier",
                    "volatility_multiplier": 1.5,
                    "description": "50% increase in market volatility"
                }
            ]
        }
    }


class RegimeScenario(BaseModel):
    """
    Scenario applying a predefined regime template.
    
    Regime templates combine multiple parameter changes to simulate
    realistic market regimes (crisis, risk-on, risk-off, etc.).
    
    Attributes:
        scenario_id: Unique identifier (e.g., "regime_crisis")
        stress_type: Always "regime_template"
        template_name: Name of the regime template
        template_parameters: Dictionary of all parameter adjustments in this regime
        description: Human-readable description
    """
    
    scenario_id: str = Field(
        ...,
        description="Unique scenario identifier"
    )
    
    stress_type: Literal["regime_template"] = Field(
        default="regime_template",
        description="Type of stress (always regime_template)"
    )
    
    template_name: str = Field(
        ...,
        description="Name of the regime template being applied"
    )
    
    template_parameters: Dict[str, float] = Field(
        ...,
        description="All parameter adjustments defined in the regime template"
    )
    
    description: str = Field(
        default="",
        description="Human-readable description of the regime"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "scenario_id": "regime_crisis",
                    "stress_type": "regime_template",
                    "template_name": "crisis",
                    "template_parameters": {
                        "tau_multiplier": 3.0,
                        "confidence_scale": 0.4,
                        "volatility_multiplier": 2.0,
                        "risk_aversion_shift": 3.0
                    },
                    "description": "Extreme market stress scenario"
                }
            ]
        }
    }


class ViewJointScenario(BaseModel):
    """
    Scenario for jointly stressing view magnitude and confidence.
    
    This creates a 2D grid of scenarios, varying both the magnitude
    of a specific view and its confidence level simultaneously.
    
    Attributes:
        scenario_id: Unique identifier (e.g., "joint_mag-1x_conf0.6")
        stress_type: Always "view_joint"
        target_label: Label of the view being stressed
        magnitude_multiplier: Multiplier for view magnitude
        confidence_scale: Scale factor for view confidence
        base_magnitude: Original view magnitude from recipe
        base_confidence: Original view confidence from recipe
        new_magnitude: Stressed magnitude value
        new_confidence: Stressed confidence value
    """
    
    scenario_id: str = Field(
        ...,
        description="Unique scenario identifier"
    )
    
    stress_type: Literal["view_joint"] = Field(
        default="view_joint",
        description="Type of stress (always view_joint)"
    )
    
    target_label: str = Field(
        ...,
        description="Label of the view being stressed"
    )
    
    magnitude_multiplier: float = Field(
        ...,
        description="Multiplier for view magnitude"
    )
    
    confidence_scale: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Scale factor for view confidence"
    )
    
    base_magnitude: float = Field(
        ...,
        description="Original view magnitude from recipe"
    )
    
    base_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Original view confidence from recipe"
    )
    
    new_magnitude: float = Field(
        ...,
        description="Stressed magnitude value"
    )
    
    new_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Stressed confidence value"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "scenario_id": "joint_mag-1x_conf0.6",
                    "stress_type": "view_joint",
                    "target_label": "NVDA outperforms META",
                    "magnitude_multiplier": -1.0,
                    "confidence_scale": 0.6,
                    "base_magnitude": 0.04,
                    "base_confidence": 0.70,
                    "new_magnitude": -0.04,
                    "new_confidence": 0.42
                }
            ]
        }
    }


# Type alias for any scenario model
AnyScenario = Union[
    Scenario,
    ViewMagnitudeScenario,
    ConfidenceScenario,
    FactorShockScenario,
    TauShiftScenario,
    VolatilityScenario,
    RegimeScenario,
    ViewJointScenario
]
