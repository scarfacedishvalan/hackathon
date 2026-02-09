from bt.core import Algo
import pandas as pd
import bt
import re
from app.services.backtest.portfolio_optimizer import PortfolioOptimizer
from app.services.price_data.data_fetch import PriceData

def iso8601_to_pandas_offset(duration):
    # Regular expression pattern to match ISO 8601 duration format with only days, months, and years
    pattern = re.compile(r'^P(?:(?P<years>\d+)Y)?(?:(?P<months>\d+)M)?(?:(?P<days>\d+)D)?$')
    
    # Match the duration string with the pattern
    match = pattern.match(duration)
    if match:
        # Extract years, months, and days from the match
        years = int(match.group('years') or 0)
        months = int(match.group('months') or 0)
        days = int(match.group('days') or 0)
        
        # Convert years, months, and days to pandas offset
        offset = pd.DateOffset(years=years, months=months, days=days)
        return offset
    else:
        raise ValueError("Invalid ISO 8601 duration format")

def handle_bounds(input_data):
    if isinstance(input_data, dict):
        return input_data
    if isinstance(input_data, tuple):
        if all(isinstance(item, tuple) for item in input_data):
            return input_data
    elif isinstance(input_data, list):
        if all(isinstance(item, tuple) for item in input_data):
            return tuple(input_data)
        elif all(isinstance(item, list) for item in input_data):
            return tuple(tuple(inner) for inner in input_data)
    return None

class MPTOptimiser(Algo):

    """
    Sets temp['weights'] based on mean-variance optimization.

    Sets the target weights based on ffn's calc_mean_var_weights. This is a
    Python implementation of Markowitz's mean-variance optimization.

    See:
        http://en.wikipedia.org/wiki/Modern_portfolio_theory#The_efficient_frontier_with_no_risk-free_asset

    Args:
        * lookback (DateOffset): lookback period for estimating volatility
        * bounds ((min, max)): tuple specifying the min and max weights for
          each asset in the optimization.
        * covar_method (str): method used to estimate the covariance. See ffn's
          calc_mean_var_weights for more details.
        * rf (float): risk-free rate used in optimization.

    Sets:
        * weights

    Requires:
        * selected

    """

    def __init__(
        self,
        lookback=pd.DateOffset(years=3),
        bounds=None,
        covar_method="standard",
        rf=0.0,
        lag=pd.DateOffset(days=0),
        returns_period = 1,
        ann_factor = None,
        target_return = None,
        optimizer_func = "sr"
    ):
        super(MPTOptimiser, self).__init__()
        self.lookback = lookback
        self.lag = lag
        self.bounds = bounds
        # print("Bounds = " + str(self.bounds))
        self.covar_method = covar_method
        self.rf = rf
        self.returns_period = returns_period
        self.ann_factor = ann_factor
        self.target_return = target_return
        self.optimizer_func = optimizer_func

    def __call__(self, target):
        selected = target.temp["selected"]

        if len(selected) == 0:
            target.temp["weights"] = {}
            return True

        if len(selected) == 1:
            target.temp["weights"] = {selected[0]: 1.0}
            return True

        t0 = target.now - self.lag
        prc = target.universe.loc[t0 - self.lookback : t0, selected]
        pricedata = PriceData(df = prc, periods=self.returns_period)
        portoptim = PortfolioOptimizer(pricedata_obj=pricedata, ann_factor=self.ann_factor)
        # tw = bt.ffn.calc_mean_var_weights(
        #     prc.to_returns().dropna(),
        #     weight_bounds=self.bounds,
        #     covar_method=self.covar_method,
        #     rf=self.rf,
        # )            
        tw = portoptim.optimize_portfolio(target_return=self.target_return, bounds=self.bounds,  optimizer =self.optimizer_func)
        target.temp["weights"] = tw.dropna()
        return True
    