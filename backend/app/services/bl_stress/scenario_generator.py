"""
Scenario Generator for Black-Litterman Stress Testing

Converts StressSpec objects into concrete numeric Scenario objects
by expanding grids and applying default values from stress_defaults.
"""

from typing import List, Dict, Any, Union
import copy

from app.services.bl_stress.stress_schema import StressSpec
from app.services.bl_stress.scenario_models import (
    Scenario,
    ViewMagnitudeScenario,
    ConfidenceScenario,
    FactorShockScenario,
    TauShiftScenario,
    VolatilityScenario,
    RegimeScenario,
    ViewJointScenario,
    AnyScenario
)
from app.services.bl_stress.stress_defaults import (
    DEFAULT_VIEW_MULTIPLIERS,
    DEFAULT_CONFIDENCE_GRID,
    DEFAULT_FACTOR_SCALE,
    DEFAULT_TAU_MULTIPLIER,
    DEFAULT_VOLATILITY_MULTIPLIER,
    get_grid_for_stress_type,
    get_regime_template
)


class ScenarioGenerator:
    """
    Generator that converts StressSpec objects into concrete Scenario objects.
    
    This class bridges the gap between symbolic stress specifications
    (e.g., "stress view magnitude with standard grid") and concrete numeric
    scenarios ready for backtest execution.
    """
    
    def __init__(self, recipe: Dict[str, Any]):
        """
        Initialize the scenario generator with a BL recipe.
        
        Args:
            recipe: Full Black-Litterman recipe dictionary containing
                    views, factors, model_parameters, etc.
        """
        self.recipe = recipe
        self._validate_recipe()
    
    def _validate_recipe(self):
        """
        Validate that recipe has required structure.
        
        Raises:
            ValueError: If recipe is missing required fields
        """
        if "model_parameters" not in self.recipe:
            raise ValueError("Recipe missing 'model_parameters' section")
        
        if "tau" not in self.recipe["model_parameters"]:
            raise ValueError("Recipe missing 'model_parameters.tau' field")
    
    def _find_view_by_label(self, label: str) -> Dict[str, Any]:
        """
        Find a view in the recipe by its label.
        
        Args:
            label: Label of the view to find
            
        Returns:
            View dictionary
            
        Raises:
            ValueError: If view with given label is not found
        """
        # Search bottom-up views
        if "bottom_up_views" in self.recipe:
            for view in self.recipe["bottom_up_views"]:
                if view.get("label") == label:
                    return view
        
        raise ValueError(f"View with label '{label}' not found in recipe")
    
    def _get_view_magnitude(self, view: Dict[str, Any]) -> float:
        """
        Extract the magnitude value from a view.
        
        Args:
            view: View dictionary
            
        Returns:
            Magnitude value (expected_outperformance or expected_return)
            
        Raises:
            ValueError: If view doesn't have a magnitude field
        """
        if "expected_outperformance" in view:
            return view["expected_outperformance"]
        elif "expected_return" in view:
            return view["expected_return"]
        else:
            raise ValueError(
                f"View '{view.get('label', 'unknown')}' missing magnitude field"
            )
    
    def generate_scenarios(self, spec: StressSpec) -> List[AnyScenario]:
        """
        Generate concrete scenarios from a StressSpec.
        
        Args:
            spec: Validated StressSpec object
            
        Returns:
            List of concrete Scenario objects
            
        Raises:
            ValueError: If spec is invalid or refers to non-existent recipe elements
        """
        stress_type = spec.stress_type
        
        if stress_type == "view_magnitude":
            return self._generate_view_magnitude_scenarios(spec)
        elif stress_type == "confidence_scale":
            return self._generate_confidence_scenarios(spec)
        elif stress_type == "factor_amplification":
            return self._generate_factor_scenarios(spec)
        elif stress_type == "tau_shift":
            return self._generate_tau_scenarios(spec)
        elif stress_type == "volatility_multiplier":
            return self._generate_volatility_scenarios(spec)
        elif stress_type == "regime_template":
            return self._generate_regime_scenarios(spec)
        elif stress_type == "view_joint":
            return self._generate_view_joint_scenarios(spec)
        else:
            raise ValueError(f"Unknown stress_type: {stress_type}")
    
    def _generate_view_magnitude_scenarios(
        self,
        spec: StressSpec
    ) -> List[ViewMagnitudeScenario]:
        """
        Generate scenarios for view magnitude stress testing.
        
        Args:
            spec: StressSpec with stress_type="view_magnitude"
            
        Returns:
            List of ViewMagnitudeScenario objects
        """
        target_label = spec.target_label
        grid_level = spec.grid_level or "standard"
        mode = spec.mode or "relative_to_base"
        
        # Find the target view
        view = self._find_view_by_label(target_label)
        base_value = self._get_view_magnitude(view)
        
        # Get grid multipliers
        multipliers = DEFAULT_VIEW_MULTIPLIERS[grid_level]
        
        # Generate scenarios
        scenarios = []
        for mult in multipliers:
            scenario_id = f"mag_{mult:+d}x"
            
            if mode == "relative_to_base":
                new_value = base_value * mult
            else:  # absolute mode
                new_value = mult * base_value  # Still multiply, but documented as absolute
            
            scenario = ViewMagnitudeScenario(
                scenario_id=scenario_id,
                stress_type="view_magnitude",
                target_label=target_label,
                multiplier=float(mult),
                base_value=base_value,
                new_value=new_value,
                mode=mode
            )
            scenarios.append(scenario)
        
        return scenarios
    
    def _generate_confidence_scenarios(
        self,
        spec: StressSpec
    ) -> List[ConfidenceScenario]:
        """
        Generate scenarios for confidence scaling stress testing.
        
        Args:
            spec: StressSpec with stress_type="confidence_scale"
            
        Returns:
            List of ConfidenceScenario objects
        """
        grid_level = spec.grid_level or "standard"
        
        # Get grid scale factors
        scale_factors = DEFAULT_CONFIDENCE_GRID[grid_level]
        
        # Generate scenarios
        scenarios = []
        for scale in scale_factors:
            scenario_id = f"conf_{scale:.1f}"
            
            description = f"{int(scale * 100)}% of base confidence"
            
            scenario = ConfidenceScenario(
                scenario_id=scenario_id,
                stress_type="confidence_scale",
                scale_factor=scale,
                description=description
            )
            scenarios.append(scenario)
        
        return scenarios
    
    def _generate_factor_scenarios(
        self,
        spec: StressSpec
    ) -> List[FactorShockScenario]:
        """
        Generate scenarios for factor amplification stress testing.
        
        Args:
            spec: StressSpec with stress_type="factor_amplification"
            
        Returns:
            List of FactorShockScenario objects
        """
        factor = spec.factor
        grid_level = spec.grid_level or "standard"
        
        # Validate that factor exists in recipe
        if "top_down_views" in self.recipe:
            top_down = self.recipe["top_down_views"]
            if "factor_model" in top_down:
                factors = top_down["factor_model"].get("factors", [])
                if factor not in factors:
                    raise ValueError(
                        f"Factor '{factor}' not found in recipe. "
                        f"Available factors: {factors}"
                    )
        
        # Get grid scale factors
        scale_factors = DEFAULT_FACTOR_SCALE[grid_level]
        
        # Generate scenarios
        scenarios = []
        for scale in scale_factors:
            scenario_id = f"factor_{factor.lower()[:3]}_{scale:.1f}x"
            
            if scale > 1.0:
                description = f"{factor} factor amplified {scale}x"
            elif scale < 1.0:
                description = f"{factor} factor dampened to {scale}x"
            else:
                description = f"{factor} factor unchanged (baseline)"
            
            scenario = FactorShockScenario(
                scenario_id=scenario_id,
                stress_type="factor_amplification",
                factor=factor,
                scale_factor=scale,
                description=description
            )
            scenarios.append(scenario)
        
        return scenarios
    
    def _generate_tau_scenarios(
        self,
        spec: StressSpec
    ) -> List[TauShiftScenario]:
        """
        Generate scenarios for tau parameter stress testing.
        
        Args:
            spec: StressSpec with stress_type="tau_shift"
            
        Returns:
            List of TauShiftScenario objects
        """
        grid_level = spec.grid_level or "standard"
        base_tau = self.recipe["model_parameters"]["tau"]
        
        # Get grid multipliers
        multipliers = DEFAULT_TAU_MULTIPLIER[grid_level]
        
        # Generate scenarios
        scenarios = []
        for mult in multipliers:
            scenario_id = f"tau_{mult:.2f}x"
            new_tau = base_tau * mult
            
            scenario = TauShiftScenario(
                scenario_id=scenario_id,
                stress_type="tau_shift",
                tau_multiplier=mult,
                base_tau=base_tau,
                new_tau=new_tau
            )
            scenarios.append(scenario)
        
        return scenarios
    
    def _generate_volatility_scenarios(
        self,
        spec: StressSpec
    ) -> List[VolatilityScenario]:
        """
        Generate scenarios for volatility multiplier stress testing.
        
        Args:
            spec: StressSpec with stress_type="volatility_multiplier"
            
        Returns:
            List of VolatilityScenario objects
        """
        grid_level = spec.grid_level or "standard"
        
        # Get grid multipliers
        multipliers = DEFAULT_VOLATILITY_MULTIPLIER[grid_level]
        
        # Generate scenarios
        scenarios = []
        for mult in multipliers:
            scenario_id = f"vol_{mult:.1f}x"
            
            if mult > 1.0:
                pct_change = int((mult - 1.0) * 100)
                description = f"{pct_change}% increase in market volatility"
            elif mult < 1.0:
                pct_change = int((1.0 - mult) * 100)
                description = f"{pct_change}% decrease in market volatility"
            else:
                description = "Baseline volatility (no change)"
            
            scenario = VolatilityScenario(
                scenario_id=scenario_id,
                stress_type="volatility_multiplier",
                volatility_multiplier=mult,
                description=description
            )
            scenarios.append(scenario)
        
        return scenarios
    
    def _generate_regime_scenarios(
        self,
        spec: StressSpec
    ) -> List[RegimeScenario]:
        """
        Generate scenario for regime template application.
        
        Args:
            spec: StressSpec with stress_type="regime_template"
            
        Returns:
            List containing single RegimeScenario object
        """
        template_name = spec.template_name
        
        # Get regime template
        template = get_regime_template(template_name)
        
        # Extract parameters (excluding description)
        template_parameters = {
            k: v for k, v in template.items()
            if k != "description"
        }
        
        scenario_id = f"regime_{template_name}"
        description = template.get("description", f"Regime: {template_name}")
        
        scenario = RegimeScenario(
            scenario_id=scenario_id,
            stress_type="regime_template",
            template_name=template_name,
            template_parameters=template_parameters,
            description=description
        )
        
        return [scenario]
    
    def _generate_view_joint_scenarios(
        self,
        spec: StressSpec
    ) -> List[ViewJointScenario]:
        """
        Generate scenarios for joint view magnitude and confidence stress testing.
        
        Creates a Cartesian product of magnitude and confidence grids.
        
        Args:
            spec: StressSpec with stress_type="view_joint"
            
        Returns:
            List of ViewJointScenario objects
        """
        target_label = spec.target_label
        mag_grid_level = spec.magnitude_grid_level or "standard"
        conf_grid_level = spec.confidence_grid_level or "standard"
        
        # Find the target view
        view = self._find_view_by_label(target_label)
        base_magnitude = self._get_view_magnitude(view)
        base_confidence = view.get("confidence", 0.8)
        
        # Get grids
        magnitude_multipliers = DEFAULT_VIEW_MULTIPLIERS[mag_grid_level]
        confidence_scales = DEFAULT_CONFIDENCE_GRID[conf_grid_level]
        
        # Generate Cartesian product of scenarios
        scenarios = []
        for mag_mult in magnitude_multipliers:
            for conf_scale in confidence_scales:
                scenario_id = f"joint_mag{mag_mult:+d}x_conf{conf_scale:.1f}"
                
                new_magnitude = base_magnitude * mag_mult
                new_confidence = base_confidence * conf_scale
                
                scenario = ViewJointScenario(
                    scenario_id=scenario_id,
                    stress_type="view_joint",
                    target_label=target_label,
                    magnitude_multiplier=float(mag_mult),
                    confidence_scale=conf_scale,
                    base_magnitude=base_magnitude,
                    base_confidence=base_confidence,
                    new_magnitude=new_magnitude,
                    new_confidence=new_confidence
                )
                scenarios.append(scenario)
        
        return scenarios


def generate_scenarios_from_spec(
    spec: StressSpec,
    recipe: Dict[str, Any]
) -> List[AnyScenario]:
    """
    Convenience function to generate scenarios from a StressSpec and recipe.
    
    Args:
        spec: Validated StressSpec object
        recipe: Full Black-Litterman recipe dictionary
        
    Returns:
        List of concrete Scenario objects
    """
    generator = ScenarioGenerator(recipe)
    return generator.generate_scenarios(spec)