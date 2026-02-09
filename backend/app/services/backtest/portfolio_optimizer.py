import numpy as np
import pandas as pd
from scipy.optimize import minimize
from app.services.price_data.data_fetch import PriceData
from numpy.linalg import multi_dot

class PortfolioOptimizer:
    def __init__(self, pricedata_obj, ann_factor=None, rf = 0):
        """
        Initialize the PortfolioOptimizer with historical returns data.
        
        Parameters:
        - returns_data: A dictionary containing investment returns data (keys: investment names, values: Pandas Series).
        """
        self._pricedata_obj = pricedata_obj
        self.returns_data = pricedata_obj.get_returns()
        self.investment_names = pricedata_obj.get_assets()
        self.timestamps = self.returns_data[self.investment_names[0]].index
        self.returns_matrix = np.array([self.returns_data[name].values for name in self.investment_names])
        if ann_factor is None:
            self.annualised_returns = self.returns_data*(365/self._pricedata_obj._periods)
        else:
            self.annualised_returns = self.returns_data*ann_factor
        self.rf = rf

    def calculate_portfolio_metrics(self, weights):
        """
        Calculate portfolio metrics for given weights.
        
        Parameters:
        - weights: A list of weights corresponding to the investments in the same order as self.investment_names.
        
        Returns:
        - portfolio_return: The expected portfolio return.
        - portfolio_std_dev: The standard deviation of the portfolio's returns.
        """
        portfolio_return = np.dot(weights, self.annualised_returns.mean())
        portfolio_std_dev = np.sqrt(multi_dot([weights.T,self.annualised_returns.cov(),weights]))
        sharpe_ratio = (portfolio_return - self.rf)/portfolio_std_dev
        return portfolio_return, portfolio_std_dev, sharpe_ratio

    def generate_efficient_frontier(self, num_points=100, optimizer = "sr"):
        """
        Generate the efficient frontier by varying portfolio weights.
        
        Parameters:
        - num_points: The number of points to generate along the efficient frontier.
        
        Returns:
        - frontier_returns: List of expected portfolio returns for each point.
        - frontier_std_devs: List of corresponding portfolio standard deviations.
        """
        frontier_returns = []
        frontier_std_devs = []
        target_returns = np.linspace(self.annualised_returns.mean(axis=1).min(), self.annualised_returns.mean(axis=1).max(), num_points)
        
        for target_return in target_returns:
            weights = self.optimize_portfolio(target_return, optimizer=optimizer)
            portfolio_return, portfolio_std_dev, sr = self.calculate_portfolio_metrics(weights)
            frontier_returns.append(portfolio_return)
            frontier_std_devs.append(portfolio_std_dev)
        
        return frontier_returns, frontier_std_devs

    def get_last_shares(self, weights, prices, amount):
        return weights*amount/prices
    
    def get_prices_evolution(self, weights, prices_df = None, amount = 10000):
        if prices_df is None:
            prices_df = self._pricedata_obj._dfraw
        init_prices = prices_df.iloc[0].values
        init_shares = self.get_last_shares(weights=weights, prices=init_prices, amount=amount)
        shares_data_resized = np.resize(init_shares, prices_df.shape)
        df_shares_prices_opt = prices_df*shares_data_resized
        return df_shares_prices_opt
    
    def min_return_constraint(self, weights, min_return):
            return np.dot(self.annualised_returns, weights) - min_return
    
    def adjust_weights(self, weights):
        n = len(self.returns_data.columns)
        if weights is None:
            return None
        
        elif len(weights) == n:
            return weights
            
        elif len(weights) < n:
            additional_weights = [(0.001, 1)] * (n - len(weights))
            adjusted_weights = weights + tuple(additional_weights)
            return adjusted_weights
        else:
            raise ValueError("Length of bounds exceeds the number of assets in universe")
    
    def optimize_portfolio(self, target_return=None, bounds=None, optimizer = "sr"):
        """
        Optimize the portfolio to achieve a target return using scipy's minimize function.
        
        Parameters:
        - target_return: The desired target portfolio return.
        
        Returns:
        - optimized_weights: Optimized portfolio weights.
        """
        n = len(self.returns_data.columns)
        num_investments = len(self.investment_names)
        
        # Initial equal weights for all investments
        initial_weights = np.ones(num_investments) / num_investments
        
        # Constraints: weights sum to 1, target return constraint
        if target_return is None:
            constraints = (
            {"type": "eq", "fun": lambda weights: np.sum(weights) - 1}
        )
        else:
            constraints = (
                {"type": "eq", "fun": lambda weights: np.sum(weights) - 1},
                {"type": "ineq", "fun": lambda weights: np.dot(self.annualised_returns, weights) - target_return}
            )
        
        # Bounds: weights between 0 and 1
        if bounds is None:
            bounds = tuple((0.001, 1) for _ in range(num_investments))
        if isinstance(bounds, dict):
            bounds = tuple((bounds.get("min_value", 0), bounds.get("max_value", 1)) for _ in range(num_investments))
        bounds = self.adjust_weights(bounds)
        if optimizer == "sr":
            optimizer_func = lambda wts: -1*self.calculate_sharpe_ratio(wts)
        elif optimizer == "sd":
            optimizer_func = self.calculate_portfolio_std_dev
        else:
            optimizer_func = optimizer
        
        # Minimize portfolio standard deviation
        result = minimize(optimizer_func, initial_weights, method="SLSQP", bounds=bounds, constraints=constraints)
        # optimized_weights = result.x
        
        return pd.Series({self.returns_data.columns[i]: result.x[i] for i in range(n)})
    
    def calculate_portfolio_std_dev(self, weights):
        """
        Calculate portfolio standard deviation for given weights.
        
        Parameters:
        - weights: A list of weights corresponding to the investments in the same order as self.investment_names.
        
        Returns:
        - portfolio_std_dev: The standard deviation of the portfolio's returns.
        """
        portfolio_return, portfolio_std_dev, sr = self.calculate_portfolio_metrics(weights)
        return portfolio_std_dev
    
    def calculate_sharpe_ratio(self, weights):
        """
        Calculate portfolio standard deviation for given weights.
        
        Parameters:
        - weights: A list of weights corresponding to the investments in the same order as self.investment_names.
        
        Returns:
        - portfolio_std_dev: The standard deviation of the portfolio's returns.
        """
        portfolio_return, portfolio_std_dev, sr = self.calculate_portfolio_metrics(weights)
        return sr
    
    def align_and_interpolate_data(self, freq="D"):
        """
        Align and interpolate data to a common frequency using Pandas resampling and interpolation.
        
        Parameters:
        - freq: The desired frequency for resampling (e.g., "D" for daily, "W" for weekly, "M" for monthly).
        
        Returns:
        - aligned_returns_data: A dictionary containing aligned and interpolated investment returns data.
        """
        aligned_returns_data = {}
        
        for name in self.investment_names:
            original_series = self.returns_data[name]
            aligned_series = original_series.resample(freq).mean()  # Resample to the desired frequency
            
            # Interpolate missing values
            aligned_series = aligned_series.interpolate(method="linear")
            
            aligned_returns_data[name] = aligned_series
        
        return aligned_returns_data

# Example usage
if __name__ == "__main__":
    # timestamps = pd.date_range(start="2022-01-01", periods=100, freq="D")
    # returns_stocks = np.random.normal(0.10, 0.20, 100)
    # returns_mutual_funds = np.random.normal(0.08, 0.15, 100)
    # returns_fixed_deposits = np.random.normal(0.06, 0.10, 100)
    
    # returns_data = {
    #     "Stocks": pd.Series(returns_stocks, index=timestamps),
    #     "MutualFunds": pd.Series(returns_mutual_funds, index=timestamps),
    #     "FixedDeposits": pd.Series(returns_fixed_deposits, index=timestamps)
    # }
    
    # optimizer = PortfolioOptimizer(returns_data)
    
    # # Align and interpolate data
    # aligned_returns_data = optimizer.align_and_interpolate_data(freq="M")  # Resample to monthly frequency
    # pricedata = PriceData()
    # optimizer = PortfolioOptimizer(pricedata)
    # numofasset = len(pricedata._dfraw.columns)
    # initial_wts = np.array(numofasset*[1./numofasset])
    # portfolio_return, portfolio_std_dev, sharpe_ratio = optimizer.calculate_portfolio_metrics(initial_wts)
    # Example efficient frontier generation using aligned data
    # frontier_returns, frontier_std_devs = optimizer.generate_efficient_frontier()
    # print("Efficient Frontier Points:")
    # for ret, std_dev in zip(frontier_returns, frontier_std_devs):
    #     print(f"Return: {ret:.4f}, Std Dev: {std_dev:.4f}")

        
    b=2