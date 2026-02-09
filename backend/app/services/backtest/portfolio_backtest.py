from app.services.backtest.portfolio_optimizer import PortfolioOptimizer
from app.services.price_data.data_fetch import PriceData
from app.services.backtest.algo_optimiser import MPTOptimiser
from datetime import timedelta
import numpy as np
import pandas as pd
import bt


REBALANCE_MAP_DICT = dict(yearly = bt.algos.RunYearly, quarterly = bt.algos.RunQuarterly, monthly = bt.algos.RunMonthly, weekly = bt.algos.RunWeekly, daily = bt.algos.RunDaily)

class PortfolioBtest:
    def __init__(self, pricedata_obj, chosen_assets = None, rebal_freq = "yearly", cov_period = 365*3, bounds=None, initial_investment = 100, returns_period = 365, rf = 0):
        self.pricedata_obj = pricedata_obj
        if chosen_assets is not None:
            self.pricedata_obj._dfraw = pd.DataFrame(self.pricedata_obj._dfraw[chosen_assets])
        self.rebalance_frequency = rebal_freq
        self.rebalance_start_period = cov_period
        self.initial_investment = initial_investment
        self.cov_period = cov_period
        self.bounds = bounds
        self.transaction_cost_rate = 0.0
        self.rebalance_dates = []
        self.pmetrics_dict = []
        self.returns_period = returns_period
        self.runafter_date = self.get_runafter_date().strftime("%Y-%m-%d")
        self.rf = rf
        self.ann_factor = None
        self.strategy_name = "s1"

    @staticmethod
    def get_interval_index(dates, ref_date, interval):
        rebalance_start_date = ref_date + timedelta(days=interval)
        min_value = np.min(np.abs((dates - rebalance_start_date).days))
        arr = np.abs((dates - rebalance_start_date).days)
        return list(arr).index(min_value)
    
    def get_weight_array_dict(self, weights = None):
        weights_array_dict = {}
        data = self.pricedata_obj._dfraw
        numofasset = len(self.pricedata_obj._dfraw.columns)
        if weights is None:
            weights = pd.Series(np.array(numofasset*[1./numofasset]), index= data.columns)
        weights_array_dict["weighed"] = weights
        for i, asset in enumerate(data.columns):
            wts = np.zeros(len(data.columns))
            wts[i] = 1
            weights = pd.Series(wts, index = data.columns)
            weights_array_dict[asset] = weights
        return weights_array_dict
    
    def get_buy_and_hold_results(self, weights = None):
        weights_arr_dict = self.get_weight_array_dict(weights=weights)
        all_strategies = []
        for strategy_name, weights_arr in weights_arr_dict.items():
            data = self.pricedata_obj._dfraw
            weights = pd.Series(weights_arr,index = data.columns)
            weighSpecifiedAlgo = bt.algos.WeighSpecified(**weights)

            # a strategy that rebalances monthly to specified weights
            strat = bt.Strategy(strategy_name,
                [
                    bt.algos.RunOnce(),
                    weighSpecifiedAlgo,
                    bt.algos.Rebalance()
                ]
            )
            backtest = bt.Backtest(
                                    strat,
                                    data,
                                    integer_positions=False
                                    )
            all_strategies.append(backtest)
        res = bt.run(*all_strategies)
        return res

    def get_runafter_date(self):
        all_dates = self.pricedata_obj._dfraw.index
        iidx = PortfolioBtest.get_interval_index(all_dates, all_dates[0], self.returns_period )
        return all_dates[iidx]
    
    def get_value_data_df(self, start_date=None):        
        price_data = self.pricedata_obj._dfraw
        if start_date is not None:
            price_data = price_data[start_date:]
        cumulative_returns = price_data / price_data.iloc[0]
        value_data = cumulative_returns * self.initial_investment
        return value_data
    
    def get_portfolio_metrics(self, df_value, weights):
        all_assets = list(df_value.columns)
        period = (list(df_value.index)[-1] - list(df_value.index)[0] ).days/365
        hold_return = np.log(df_value.iloc[-1]/df_value.iloc[0])/period
        price_obj = PriceData(df = df_value)
        portoptim = PortfolioOptimizer(price_obj)
        portfolio_return, portfolio_std_dev, sharpe_ratio = portoptim.calculate_portfolio_metrics(weights=weights)

    def run_bt_new(self, target_return = None,  optimizer_func = "sr"):
        rebalance_func = REBALANCE_MAP_DICT[self.rebalance_frequency]

        s = bt.Strategy(self.strategy_name, [rebalance_func(),
                       bt.algos.SelectAll(),
                       bt.algos.RunAfterDate(self.runafter_date),
                       MPTOptimiser(        lookback=pd.DateOffset(days = self.cov_period),
                                            bounds=self.bounds,
                                            covar_method="standard",
                                            rf=self.rf,
                                            lag=pd.DateOffset(days=0),
                                            returns_period = self.returns_period,
                                            ann_factor = self.ann_factor,
                                            target_return = target_return,
                                            optimizer_func = optimizer_func
                                    ),
                       bt.algos.Rebalance()
                      ])
        test = bt.Backtest(s, self.pricedata_obj._dfraw)
        results = bt.run(test)
        return results
    

    def get_backtest_data(self, target_returns, optimiser_func = "sr"):
        price_data = self.pricedata_obj._dfraw
        dates = price_data.index
        # initial_investment = 100  # Initial investment amount
        current_weights = None
        portfolio_values = []
        rebalance_weights = {}
        rebalance_start_index = PortfolioBtest.get_interval_index(dates=dates, ref_date=dates[0], interval=self.rebalance_start_period)
        # Iterate through rebalancing dates
        start_index = 0
        value_datalist = []
        value_data = self.get_value_data_df()
        dfsharelist_opt = []
        numofasset = len(price_data.columns)
        initial_wts = np.array(numofasset*[1./numofasset])
        start_idx=0
        i=rebalance_start_index
        port_value_opt = self.initial_investment
        cov_period = self.cov_period
        try:
            returns_iter = iter(target_returns)
        except TypeError:
           returns_iter = iter([target_returns]*len(dates))
        wtlist = []
        while i < len(dates):
            # Extract price data up to the current rebalance date
            if cov_period is None or i==rebalance_start_index:
                start_idx = 0
            else:
                start_idx = PortfolioBtest.get_interval_index(dates, dates[i], -1*cov_period)
            prices_up_to_rebalance = price_data.loc[dates[start_idx]:dates[i]]
            last_prices = prices_up_to_rebalance.iloc[-1].values
            # Calculate target returns for the current rebalance
            current_target_return = next(returns_iter)
            # Optimize portfolio weights using the provided optimizer function
            price_obj = PriceData(df = prices_up_to_rebalance, periods=self.rebalance_frequency)
            portoptim = PortfolioOptimizer(price_obj)
            optimal_weights = portoptim.optimize_portfolio(target_return=current_target_return, bounds=self.bounds, optimizer = optimiser_func)
            optimal_weights = optimal_weights.values
            # Rebalance the portfolio
            last_shares_opt = optimal_weights*port_value_opt/last_prices
            rebalance_end_index = PortfolioBtest.get_interval_index(dates, dates[i], self.rebalance_frequency)
            price_data_slice = price_data.loc[dates[i]:dates[rebalance_end_index]]
            data_shares_opt = np.resize(last_shares_opt, price_data_slice.shape)
            df_shares_prices_opt = price_data_slice*data_shares_opt        
            dfsharelist_opt.append(df_shares_prices_opt)
            value_data_slice = value_data.loc[dates[i]:dates[rebalance_end_index]]
            portfolio_value = (value_data_slice * optimal_weights).sum(axis=1)
            # Save rebalance weights to the dictionary
            self.rebalance_dates.append(dates[i])
            rebalance_weights[dates[i]] = optimal_weights
            d = {"date": dates[i]}
            wt_dict = dict(zip(list(self.pricedata_obj._dfraw.columns), optimal_weights))            
            d.update(wt_dict)
            wtlist.append(d)
            if current_weights is not None:
                transaction_costs = np.abs(optimal_weights - current_weights) * prices_up_to_rebalance.iloc[-1] * self.transaction_cost_rate
            else:
                transaction_costs = np.zeros(len(optimal_weights))
            portfolio_values.append(portfolio_value)
            port_value_opt = df_shares_prices_opt.sum(axis=1).iloc[-1]
            i = rebalance_end_index
            if list(price_data_slice.index)[-1] >= list(price_data.index)[-1]:
                break 

        # Create a DataFrame with time-indexed portfolio values
        df_shares_opt_all = pd.concat(dfsharelist_opt)
        df_shares_opt_all["pfolio_value"] = df_shares_opt_all.sum(axis=1)
        df_portfolio = pd.concat(portfolio_values)
        df_weights = pd.DataFrame(wtlist)
        dfw = df_weights.set_index("date")
        df_shares_opt_all = df_shares_opt_all.join(dfw, rsuffix = "_weight").fillna(method = 'ffill')
        return df_shares_opt_all
    

if __name__ == "__main__":
    print("This file should be run using backend/run_backtest.py")
    print("Usage: python run_backtest.py")
