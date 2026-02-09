from nsepython import *

end_date = datetime.datetime.now().strftime("%d-%m-%Y")
end_date = str(end_date)

start_date = (datetime.datetime.now()- datetime.timedelta(days=65)).strftime("%d-%m-%Y")
start_date = str(start_date)

symbol = "SBIN"
series = "EQ"

df = equity_history(symbol,series,start_date,end_date)