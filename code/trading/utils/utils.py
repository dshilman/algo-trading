date_format = "%Y-%m-%d %H:%M:%S"
ticker_data_size=120
frequency_min = 5
granularity="S30"
count=frequency_min * 2 * ticker_data_size

def convert_perc_to_pips(units, perc, price):

    target_price = convert_perc_to_ls_price(units, perc, price)
    return round(abs(price - target_price), 4)

 
def convert_perc_to_ls_price(units, perc, price):

    return round(price - (1 if units > 0 else -1) * price * perc, (4 if price < 100 else 0))

def convert_perc_to_tp_price(units, perc, price):

    return round(price + (1 if units > 0 else -1) * price * perc, (4 if price < 100 else 0))

if __name__ == "__main__":
    print(convert_perc_to_pips(55000, 0.0015, 1.10570))