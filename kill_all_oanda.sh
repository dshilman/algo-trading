processes=("/bin/sh /home/ec2-user/algo-trading/trader_oanda_EUR_HKD.sh"
"/bin/sh /home/ec2-user/algo-trading/trader_oanda_EUR_USD.sh"
"/bin/sh /home/ec2-user/algo-trading/trader_oanda_USD_HKD.sh"
"/bin/sh /home/ec2-user/algo-trading/trader_oanda_GBP_USD.sh"
"/bin/sh /home/ec2-user/algo-trading/trader_oanda_USD_CHF.sh"
"/bin/sh /home/ec2-user/algo-trading/trader_oanda_USD_CAD.sh"
)

# Loop through each process name
for process_name in "${processes[@]}"; do
    # Call kill_process.sh script for each process name
    ./kill_process.sh "$process_name"
done