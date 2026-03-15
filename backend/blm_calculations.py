# bl_full_steps_app.py
import numpy as np
from dash import Dash, html, dcc
import dash
from dash import html, Output, Input, ctx, State
import dash_bootstrap_components as dbc
import uuid
# ----------------------------
# Example input data
# ----------------------------


# ----------------------------
# Convert matrices to LaTeX
# ----------------------------
def np_to_latex(A):
    """Convert numpy array to LaTeX bmatrix."""
    if A.ndim == 1:
        rows = [f"{x:.4f}" for x in A]
        body = " \\\\ ".join(rows)
        return r"\begin{bmatrix}" + body + r"\end{bmatrix}"
    rows = []
    for row in A:
        # if row is of float type
        val = row[0]
        if isinstance(val, (float, np.floating)):
            max_val = np.max(np.abs(row))
            if max_val < 0.0001:
                formatted = [f"{x:.2e}" for x in row]
            else:
                formatted = [f"{x:.4f}" for x in row]
        else:
            formatted = [str(x) for x in row]
        
        rows.append(" & ".join(formatted))
    body = " \\\\ ".join(rows)
    return r"\begin{bmatrix}" + body + r"\end{bmatrix}"

# ----------------------------
# Build LaTeX sections
# ----------------------------
def build_latex_sections(tau, Sigma, pi, P, Q, Omega, posterior_returns, posterior_cov):
    formula_section = r"""
    $$
    \textbf{Black–Litterman Model}
    $$

    $$
    E[R]_{BL} = \left[(\tau \Sigma)^{-1} + P^T \Omega^{-1} P \right]^{-1}
    \left[(\tau \Sigma)^{-1}\pi + P^T \Omega^{-1}Q\right]
    $$

    $$
    \Sigma_{BL} = \Sigma + \left[(\tau \Sigma)^{-1} + P^T \Omega^{-1} P \right]^{-1}
    $$
    """

    inputs_section = rf"""
    $$
    \tau = {tau}
    $$

    $$
    \Sigma = {np_to_latex(Sigma)}
    $$

    $$
    \pi = {np_to_latex(pi)}
    $$

    $$
    P = {np_to_latex(P)}
    $$

    $$
    Q = {np_to_latex(Q)}
    $$

    $$
    \Omega = {np_to_latex(Omega)}
    $$
    """

    steps_section = r"""
    $$
    \textbf{Computation Steps \& Results}
    $$
    """

    results_section = rf"""
    $$
    E[R]_{{BL}} = {np_to_latex(posterior_returns)}
    $$

    $$
    \Sigma_{{BL}} = {np_to_latex(posterior_cov)}
    $$
    """

    return html.Div([
    html.H2("Black–Litterman Model: Step-by-Step Computation", style={"textAlign": "center"}),

    html.Div([
        html.H3("Formulas"),
        dcc.Markdown(formula_section, mathjax=True, style={"fontSize": "20px"}),

        html.H3("Inputs"),
        dcc.Markdown(inputs_section, mathjax=True, style={"fontSize": "20px"}),

        html.H3("Posterior Returns & Covariance"),
        html.Div([
            dcc.Markdown(results_section, mathjax=True, style={"fontSize": "20px"})
        ])
    ], style={"maxWidth": "900px", "margin": "auto"})
    ])



def make_collapsible(app, component, title="Toggle Section"):

    base_id = getattr(component, "id", None)
    if base_id is None:
        base_id = f"comp-{uuid.uuid4().hex[:6]}"
        component.id = base_id  # assign if not set

    collapse_id = f"{base_id}-collapse"
    button_id = f"{base_id}-button"

    collapse = html.Div(
    [
        dbc.Button(
            title,
            id=button_id,
            className="mb-3",
            color="primary",
            n_clicks=0,
        ),
        dbc.Collapse(
            dbc.Card(dbc.CardBody(component)),
            id=collapse_id,
            is_open=False,
        ),
    ]
    )

    @app.callback(
            Output(collapse_id, "is_open"),
            [Input(button_id, "n_clicks")],
            [State(collapse_id, "is_open")],
        )
    def toggle_collapse(n, is_open):
        if n:
            return not is_open
        return is_open
    
    return app, collapse


def add_callbacks(app):
    @app.callback(
            Output("collapse", "is_open"),
            [Input("collapse-button", "n_clicks")],
            [State("collapse", "is_open")],
        )
    def toggle_collapse(n, is_open):
        if n:
            return not is_open
        return is_open
    return app

def create_collapsible_section():
    cov_matrix, P, Q, omega, tau, pi, posterior_returns, posterior_cov, cleaned_weights, performance = first_execute()
    full_layout = build_latex_sections(tau, cov_matrix.values, pi, P, Q, omega, posterior_returns, posterior_cov.values)

    
if __name__ == "__main__":
    from blm_executor import first_execute
    # tau = 0.05
    # Sigma = np.array([
    #     [0.04, 0.006, 0.004],
    #     [0.006, 0.09, 0.008],
    #     [0.004, 0.008, 0.07]
    # ])
    # pi = np.array([0.08, 0.06, 0.07])
    # P = np.array([[1, -1, 0],
    #             [0, 1, -1]], dtype=int)
    # Q = np.array([0.03, 0.02])
    # Omega = np.diag([0.0001, 0.0001])

    # # ----------------------------
    # # Compute posterior estimates
    # # ----------------------------
    # # Black-Litterman formulas:
    # # E[R]_BL = [ (τΣ)^(-1) + PᵀΩ^(-1)P ]^(-1) [ (τΣ)^(-1)π + PᵀΩ^(-1)Q ]
    # # Σ_BL = Σ + [ ( (τΣ)^(-1) + PᵀΩ^(-1)P )^(-1) ]

    # tau_Sigma = tau * Sigma
    # inv_tauSigma = np.linalg.inv(tau_Sigma)
    # inv_Omega = np.linalg.inv(Omega)

    # middle = inv_tauSigma + P.T @ inv_Omega @ P
    # M_inv = np.linalg.inv(middle)

    # posterior_returns = M_inv @ (inv_tauSigma @ pi + P.T @ inv_Omega @ Q)
    # posterior_cov = Sigma + M_inv

        # ----------------------------
    # Build Dash app
    # ----------------------------
    app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    cov_matrix, P, Q, omega, tau, pi, posterior_returns, posterior_cov, cleaned_weights, performance = first_execute()
    full_layout = build_latex_sections(tau, cov_matrix.values, pi, P, Q, omega, posterior_returns, posterior_cov.values)
    app, collapsible_layout = make_collapsible(app, full_layout, title="Show/Hide Black–Litterman Computation Steps")
    app.layout = html.Div([collapsible_layout], style={"padding": "20px"})
    # app = add_callbacks(app)
    app.run_server(debug=True)
