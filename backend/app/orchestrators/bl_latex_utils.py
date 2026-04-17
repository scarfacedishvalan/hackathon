"""
Black-Litterman LaTeX Formatting Utilities

Converts numpy arrays, pandas Series, and matrices to LaTeX format
for mathematical display.
"""

from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Any, Dict, List


def np_to_latex(A: np.ndarray, precision: int = 4) -> str:
    """
    Convert numpy array to LaTeX bmatrix.
    
    Args:
        A: numpy array (1D or 2D)
        precision: number of decimal places
        
    Returns:
        LaTeX string in bmatrix format
    """
    if A.ndim == 1:
        rows = [f"{x:.{precision}f}" for x in A]
        body = " \\\\ ".join(rows)
        return r"\begin{bmatrix}" + body + r"\end{bmatrix}"
    
    rows = []
    for row in A:
        # Check if values are very small
        max_val = np.max(np.abs(row))
        if max_val < 0.0001 and max_val > 0:
            formatted = [f"{x:.2e}" for x in row]
        else:
            formatted = [f"{x:.{precision}f}" for x in row]
        rows.append(" & ".join(formatted))
    
    body = " \\\\ ".join(rows)
    return r"\begin{bmatrix}" + body + r"\end{bmatrix}"


def series_to_latex(s: pd.Series, precision: int = 4, with_names: bool = True) -> str:
    """
    Convert pandas Series to LaTeX column vector.
    
    Args:
        s: pandas Series
        precision: number of decimal places
        with_names: if True, include asset names as comments
        
    Returns:
        LaTeX string
    """
    if with_names:
        rows = [f"{val:.{precision}f} & \\text{{{name}}}" for name, val in s.items()]
        body = " \\\\ ".join(rows)
        return r"\begin{array}{rl}" + body + r"\end{array}"
    else:
        arr = s.values
        return np_to_latex(arr, precision=precision)


def _format_p_row_with_assets(P_row: np.ndarray, assets: List[str], precision: int = 1) -> str:
    """
    Format a P matrix row as LaTeX with asset labels for non-zero values.
    
    Args:
        P_row: Single row from P matrix
        assets: List of asset names
        precision: number of decimal places
        
    Returns:
        LaTeX string showing row with asset annotations
    """
    # Build inline representation highlighting non-zero values
    parts = []
    for i, val in enumerate(P_row):
        if abs(val) > 1e-6:  # Non-zero
            if val == 1.0:
                parts.append(f"\\text{{{assets[i]}}}")
            elif val == -1.0:
                parts.append(f"-\\text{{{assets[i]}}}")
            else:
                parts.append(f"{val:.{precision}f}\\cdot\\text{{{assets[i]}}}")
    
    if not parts:
        # All zeros
        return r"\mathbf{0}"
    
    # Join with + signs (handling negatives)
    formula = parts[0]
    for part in parts[1:]:
        if part.startswith('-'):
            formula += f" {part}"
        else:
            formula += f" + {part}"
    
    # Also show as vector
    vector = np_to_latex(P_row, precision=precision)
    
    return f"[{formula}] = {vector}"


def build_calculation_latex(calc_steps: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Build LaTeX formatted sections from calculation steps.
    
    Args:
        calc_steps: Dictionary containing all BL calculation steps
        
    Returns:
        List of section dictionaries with title and latex content
    """
    sections = []
    
    # 1. Model Formulas
    sections.append({
        "title": "Black–Litterman Formulas",
        "latex": r"""
$$
\textbf{Posterior Returns}
$$

$$
E[R]_{BL} = \left[(\tau \Sigma)^{-1} + P^T \Omega^{-1} P \right]^{-1}
\left[(\tau \Sigma)^{-1}\pi + P^T \Omega^{-1}Q\right]
$$

$$
\textbf{Posterior Covariance}
$$

$$
\Sigma_{BL} = \Sigma + \left[(\tau \Sigma)^{-1} + P^T \Omega^{-1} P \right]^{-1}
$$
        """
    })
    
    # 2. Inputs (excluding P and Q which will be in View Translation)
    tau = calc_steps.get("tau", 0.05)
    Sigma = calc_steps.get("Sigma")
    pi = calc_steps.get("pi")
    Omega = calc_steps.get("Omega")
    assets = calc_steps.get("assets", [])
    factor_matrix = calc_steps.get("factor_matrix")
    factor_names = calc_steps.get("factor_names")

    # Build factor exposure table as LaTeX array if available
    factor_block = ""
    if factor_matrix is not None and factor_names:
        header = " & ".join([f"\\text{{{f}}}" for f in factor_names])
        rows = []
        for i, asset in enumerate(assets):
            vals = " & ".join([f"{v:.2f}" for v in factor_matrix[i]])
            rows.append(f"\\text{{{asset}}} & {vals}")
        table_body = " \\\\ ".join(rows)
        factor_block = f"""
$$
\\text{{Factor Exposure Matrix }} B \\text{{ (rows = assets, cols = factors)}}
$$

$$
\\begin{{array}}{{l{'c' * len(factor_names)}}}
\\text{{Asset}} & {header} \\\\
\\hline
{table_body}
\\end{{array}}
$$
"""

    inputs_latex = f"""
$$
\\tau \\text{{ (Uncertainty Scaling Parameter)}} = {tau}
$$

$$
\\text{{Assets: }} [{', '.join(assets)}]
$$

$$
\\pi \\text{{ (Market Equilibrium Returns)}}
$$

$$
{series_to_latex(pi, with_names=True) if isinstance(pi, pd.Series) else np_to_latex(pi)}
$$
{factor_block}
$$
\\Sigma \\text{{ (Covariance Matrix)}}
$$

$$
{np_to_latex(Sigma)}
$$

$$
\\Omega \\text{{ (View Uncertainty Diagonal Matrix)}}
$$

$$
{np_to_latex(Omega)}
$$
    """
    
    sections.append({
        "title": "Model Inputs",
        "latex": inputs_latex
    })
    
    # 3. View Translation - Show how each view translates to P and Q
    bottom_up_views = calc_steps.get("bottom_up_view_details", [])
    top_down_views = calc_steps.get("top_down_view_details", [])
    P = calc_steps.get("P")
    Q = calc_steps.get("Q")
    Omega = calc_steps.get("Omega")
    
    if bottom_up_views or top_down_views:
        view_translation_parts = []
        
        # Bottom-Up Views
        if bottom_up_views:
            view_translation_parts.append("""
$$
\\textbf{Bottom-Up Views}
$$
            """)
            
            for i, view in enumerate(bottom_up_views, 1):
                label = view.get('label', f'View {i}')
                description = view.get('description', '')
                P_row = view.get('P_row')
                Q_val = view.get('Q_val')
                confidence = view.get('confidence')
                row_idx = view.get('row_index', i-1)
                
                # Format P row with asset labels
                p_row_latex = _format_p_row_with_assets(P_row, assets)
                
                # Get Omega value safely
                omega_val = Omega[row_idx, row_idx] if Omega is not None and row_idx < Omega.shape[0] else 0.0
                
                view_translation_parts.append(f"""
$$
\\text{{View {i}: {label}}}
$$

$$
\\text{{{description}}}
$$

$$
P[{row_idx}] = {p_row_latex}
$$

$$
Q[{row_idx}] = {Q_val:.4f}
$$

$$
\\text{{Confidence: {confidence:.2f}}} \\quad \\Rightarrow \\quad \\Omega[{row_idx},{row_idx}] = {omega_val:.6f}
$$
                """)
        
        # Top-Down Views
        if top_down_views:
            view_translation_parts.append("""
$$
\\textbf{Top-Down Factor Views}
$$
            """)
            
            for i, view in enumerate(top_down_views, 1):
                label = view.get('label', f'Factor View {i}')
                description = view.get('description', '')
                factor = view.get('factor', '')
                P_row = view.get('P_row')
                Q_val = view.get('Q_val')
                confidence = view.get('confidence')

                # P_row is now the factor exposure column B[:,factor_idx]
                # Format it to show which assets carry this factor and by how much
                p_row_latex = _format_p_row_with_assets(P_row, assets, precision=2)

                view_translation_parts.append(f"""
$$
\\text{{Factor View {i}: {label}}}
$$

$$
\\text{{{description}}}
$$

$$
\\text{{Factor exposure vector }} B[:,\\text{{{factor}}}] = {p_row_latex}
$$

$$
\\Delta f = {Q_val:+.4f}
$$

$$
\\text{{Confidence: {confidence:.2f}}} \\quad \\Rightarrow \\quad \\Delta\\mu = B[:,\\text{{{factor}}}] \\times {Q_val:+.4f}
$$
                """)
        
        # Final combined matrices
        view_translation_parts.append(f"""
$$
\\textbf{{Combined Pick Matrix (P)}}
$$

$$
\\text{{Each row represents one view. Total: {len(bottom_up_views)} bottom-up + {len(top_down_views)} top-down}}
$$

$$
P = {np_to_latex(P)}
$$

$$
\\textbf{{Combined View Returns (Q)}}
$$

$$
Q = {np_to_latex(Q)}
$$
        """)
        
        view_translation_latex = "\n".join(view_translation_parts)
        
        sections.append({
            "title": "View Translation",
            "latex": view_translation_latex
        })
    
    # 4. Intermediate Calculations
    if "tau_Sigma" in calc_steps:
        intermediate_latex = f"""
$$
\\text{{Step 1: Scaled Prior Covariance}}
$$

$$
\\tau \\Sigma = {tau} \\times \\Sigma
$$

$$
{np_to_latex(calc_steps["tau_Sigma"], precision=6)}
$$

$$
\\text{{Step 2: Inverse of Scaled Covariance}}
$$

$$
(\\tau \\Sigma)^{{-1}}
$$

$$
{np_to_latex(calc_steps["tau_Sigma_inv"], precision=6)}
$$

$$
\\text{{Step 3: Inverse of View Uncertainty}}
$$

$$
\\Omega^{{-1}}
$$

$$
{np_to_latex(calc_steps["Omega_inv"], precision=6)}
$$

$$
\\text{{Step 4: Posterior Precision Matrix}}
$$

$$
M = (\\tau \\Sigma)^{{-1}} + P^T \\Omega^{{-1}} P
$$

$$
{np_to_latex(calc_steps["posterior_precision"], precision=6)}
$$
        """
        
        sections.append({
            "title": "Intermediate Calculations",
            "latex": intermediate_latex
        })
    
    # 5. Results
    posterior_returns = calc_steps.get("posterior_returns")
    posterior_cov = calc_steps.get("posterior_cov")
    
    results_latex = f"""
$$
\\text{{Posterior Expected Returns (per asset)}}
$$

$$
E[R]_{{BL}}
$$

$$
{series_to_latex(posterior_returns, with_names=True) if isinstance(posterior_returns, pd.Series) else np_to_latex(posterior_returns)}
$$

$$
\\text{{Posterior Covariance Matrix}}
$$

$$
\\Sigma_{{BL}}
$$

$$
{np_to_latex(posterior_cov)}
$$
    """
    
    sections.append({
        "title": "Posterior Results",
        "latex": results_latex
    })
    
    # 6. Optimal Portfolio Weights (Max Sharpe)
    optimal_weights = calc_steps.get("optimal_weights")
    
    if optimal_weights is not None:
        weights_latex = f"""
$$
\\text{{Optimal Portfolio Weights (Max Sharpe Ratio)}}
$$

$$
\\text{{These weights maximize the Sharpe ratio using the posterior returns and covariance.}}
$$

$$
w^*
$$

$$
{series_to_latex(optimal_weights, with_names=True, precision=6) if isinstance(optimal_weights, pd.Series) else np_to_latex(optimal_weights, precision=6)}
$$
        """
        
        sections.append({
            "title": "Optimal Portfolio Weights",
            "latex": weights_latex
        })
    
    return sections
