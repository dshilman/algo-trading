# Forex Trading Bot

An automated forex trading system built with Python that executes algorithmic trading strategies on the OANDA platform. The bot supports multiple trading strategies (MACD and Mean Reversion) and can trade multiple currency pairs simultaneously.

## Features

- **Multiple Trading Strategies**
  - MACD-based momentum trading
  - Mean reversion strategies
  - Configurable technical indicators (Bollinger Bands, RSI, EMA, SMA)

- **Real-time Trading**
  - Live price streaming from OANDA API
  - Automated order execution with stop-loss and take-profit
  - Position tracking and P&L calculation
  - Thread-safe concurrent trading across multiple pairs

- **Risk Management**
  - Configurable stop-loss and take-profit percentages
  - Trailing stop-loss support
  - Spread filtering
  - Trading pause windows (e.g., during high volatility events)

- **Backtesting Framework**
  - Historical data analysis
  - Strategy performance evaluation
  - Excel/Pickle export for results

- **AWS Deployment**
  - EC2 instance hosting
  - Lambda functions for automated start/stop
  - Scheduled trading sessions

## Architecture

```
├── code/
│   ├── trading/              # Live trading bot
│   │   ├── api/              # OANDA API integration
│   │   ├── dom/              # Domain objects (Order, Trade, Session)
│   │   ├── strategies/       # Trading strategy implementations
│   │   │   ├── base/         # Base strategy classes
│   │   │   ├── macd_1.py     # MACD strategy variant 1
│   │   │   ├── macd_2.py     # MACD strategy variant 2
│   │   │   └── mean_reverse_*.py
│   │   ├── utils/            # Technical indicators & utilities
│   │   ├── pairs.ini         # Strategy configurations per pair
│   │   └── trading_bot.py    # Main trading bot
│   ├── backtesting/          # Backtesting framework
│   ├── lambda/               # AWS Lambda functions
│   └── requirements.txt      # Python dependencies
├── config/
│   ├── oanda.cfg             # OANDA API credentials
│   └── crontab.txt           # Cron job configuration
├── logs/                     # Trading logs
├── start_trading.sh          # Start all trading bots
├── stop_trading.sh           # Stop all trading bots
└── trader_oanda_*.sh         # Individual pair trading scripts
```

## Prerequisites

- Python 3.8+
- OANDA trading account (live or practice)
- AWS account (for EC2 deployment)
- Linux/Unix environment (tested on Ubuntu)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd forex-trading-bot
```

### 2. Install Dependencies

```bash
pip install -r code/requirements.txt
```

Required packages:
- pandas - Data manipulation
- numpy - Numerical computing
- scikit-learn - Machine learning (for technical indicators)
- requests - HTTP client for API calls
- boto3 - AWS SDK
- tabulate - Trade report formatting
- openpyxl - Excel export

### 3. Configure OANDA Credentials

Edit `config/oanda.cfg`:

```ini
[oanda]
account_id = YOUR_ACCOUNT_ID
access_token = YOUR_ACCESS_TOKEN
account_type = practice  # or 'live' for real trading
```

**Security Note:** For production, use environment variables instead:
```bash
export OANDA_ACCOUNT_ID="your_account_id"
export OANDA_ACCESS_TOKEN="your_access_token"
```

### 4. Configure Trading Strategies

Edit `code/trading/pairs.ini` to configure strategies for each currency pair:

```ini
[EUR_USD#1]
pair=EUR_USD
units_to_trade=50000
trading_spread=0.00017
SMA=100
dev=3
sl_perc=0.0015
tp_perc=0.0035
trailing_sl=False
strategy=macd_1.TradingStrategy
```

Key parameters:
- `units_to_trade` - Position size
- `sl_perc` - Stop loss percentage
- `tp_perc` - Take profit percentage
- `SMA` - Simple moving average period
- `dev` - Bollinger Band standard deviations
- `trading_spread` - Maximum acceptable spread

## Usage

### Local Development

#### Start Trading Bot (Single Pair)

```bash
python3 code/trading/trading_bot.py EUR_USD#1
```

#### Start All Configured Pairs

```bash
./start_trading.sh
```

#### Stop All Trading Bots

```bash
./stop_trading.sh
```

#### Run Backtesting

```bash
cd code/backtesting
python3 trading_bot_backtest.py EUR_USD#1 --days 30 --refresh True
```

Options:
- `--days` - Number of historical days to test
- `--refresh` - Fetch fresh data from OANDA (True/False)

### AWS EC2 Deployment

#### 1. Launch EC2 Instance

- AMI: Ubuntu 22.04 LTS
- Instance Type: t3.micro or larger
- Security Group: Allow SSH (port 22)
- Tag: `Name=demo-trading-server-new`

#### 2. Setup EC2 Instance

```bash
# SSH into instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Install Python and dependencies
sudo apt update
sudo apt install python3 python3-pip git -y

# Clone repository
git clone <repository-url>
cd forex-trading-bot

# Install dependencies
pip3 install -r code/requirements.txt

# Configure credentials
nano config/oanda.cfg
```

#### 3. Setup Cron Jobs

```bash
crontab -e
```

Add entries from `config/crontab.txt`:
```
# Start trading at 9:00 AM EST Monday-Friday
0 14 * * 1-5 cd /home/ubuntu/forex-trading-bot && ./start_trading.sh >> logs/cron.log 2>&1

# Stop trading at 5:00 PM EST Monday-Friday
0 22 * * 1-5 cd /home/ubuntu/forex-trading-bot && ./stop_trading.sh >> logs/cron.log 2>&1
```

#### 4. Deploy Lambda Functions (Optional)

For automated EC2 start/stop:

```bash
cd code/lambda

# Create deployment package
zip -r start_ec2.zip start_ec2_lambda.py
zip -r stop_ec2.zip stop_ec2_lambda.py

# Upload to AWS Lambda via AWS Console or CLI
aws lambda create-function \
  --function-name StartTradingEC2 \
  --runtime python3.9 \
  --role arn:aws:iam::YOUR_ACCOUNT:role/lambda-ec2-role \
  --handler start_ec2_lambda.lambda_handler \
  --zip-file fileb://start_ec2.zip
```

Configure EventBridge rules to trigger Lambda on schedule.

## Trading Strategies

### MACD Strategy (macd_1.py, macd_2.py)

Momentum-based strategy using MACD crossovers:

**Entry Signals:**
- **Long:** Near bullish MACD crossover + positive EMA slope + negative prediction error + momentum confirmation
- **Short:** Near bearish MACD crossover + negative EMA slope + positive prediction error + momentum confirmation

**Exit Signals:**
- Stop loss triggered
- Take profit reached
- MACD reversal
- Time-based exit (configurable)

### Mean Reversion Strategy (mean_reverse_1.py, mean_reverse_2.py)

Bollinger Band-based mean reversion:

**Entry Signals:**
- **Long:** Price crosses below lower Bollinger Band + RSI > high threshold
- **Short:** Price crosses above upper Bollinger Band + RSI < low threshold

**Exit Signals:**
- Price returns to SMA
- Stop loss triggered
- Take profit reached

## Monitoring

### Logs

Logs are stored in `logs/trading/`:
- `{PAIR}_{STRATEGY}_app.log` - Trading activity
- `oanda_api.log` - API interactions

### Trade Reports

After each session, the bot prints:
- Total P&L
- Number of long/short trades
- Trade details (entry/exit prices, duration, profit)

Example output:
```
Finished Trading EUR_USD with PL: $1,234.56
# of long trades: 5, # of short trades: 3, open trades: 0

datetime             trade          units    price    trade_pnl    trade_duration    total pnl
-------------------  -----------  -------  -------  -----------  ----------------  -----------
2026-01-25 14:30:00  Open Long      50000   1.0850                                    $0.00
2026-01-25 15:45:00  Close Long    -50000   1.0875      $125.00  1 hr 15 min          $125.00
```

## Performance Optimizations

Recent improvements (v2.0):
- **4x faster** candle aggregation (optimized DataFrame operations)
- **Thread-safe** concurrent trading (eliminated race conditions)
- **Position reconciliation** on startup (prevents drift)
- **Improved error handling** (network vs API errors)

See `IMPROVEMENTS_APPLIED.md` for details.

## Configuration Reference

### Strategy Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `pair` | Currency pair | EUR_USD |
| `units_to_trade` | Position size | 50000 |
| `trading_spread` | Max acceptable spread | 0.00017 |
| `trading_std` | Min volatility to trade | 0.00055 |
| `SMA` | Moving average period | 100 |
| `dev` | Bollinger Band std devs | 3 |
| `high_rsi` | RSI overbought level | 75 |
| `low_rsi` | RSI oversold level | 25 |
| `sl_perc` | Stop loss % | 0.0015 (0.15%) |
| `tp_perc` | Take profit % | 0.0035 (0.35%) |
| `trailing_sl` | Enable trailing SL | True/False |
| `pause_start_est` | Pause start time | 16:50:00 |
| `pause_end_est` | Pause end time | 17:00:00 |
| `keep_trade_open_time` | Max trade duration (min) | 90 |

## Risk Disclaimer

**IMPORTANT:** This software is for educational purposes only. Forex trading involves substantial risk of loss and is not suitable for all investors. Past performance is not indicative of future results.

- Never trade with money you cannot afford to lose
- Always test strategies in a practice account first
- Monitor your positions regularly
- Understand the risks of automated trading
- The authors are not responsible for any financial losses

## Troubleshooting

### Bot Not Starting

```bash
# Check if already running
ps aux | grep trading_bot.py

# Check logs
tail -f logs/trading/*_app.log

# Verify credentials
python3 -c "from trading.api.oanda_api import OandaApi; api = OandaApi('config/oanda.cfg'); print(api.get_account_summary())"
```

### No Trades Being Executed

- Check spread: Current spread may exceed `trading_spread` threshold
- Check volatility: May not meet `trading_std` requirement
- Check pause window: May be in configured pause period
- Review logs for strategy conditions

### Position Mismatch

The bot automatically reconciles positions on startup. Check logs:
```
Position mismatch detected. Actual: 50000, Expected: 0
Position reconciled: 50000 units
```

## Development

### Running Tests

```bash
# Unit tests
python3 code/unit/trading_bot_unit.py

# Backtesting
python3 code/backtesting/trading_bot_backtest.py EUR_USD#1 --days 7
```

### Adding New Strategies

1. Create new strategy file in `code/trading/strategies/`
2. Inherit from appropriate base class (`TradingStrategyMACD` or `TradingStrategyMeanReverse`)
3. Implement `check_if_need_open_trade()` and `check_if_need_close_trade()`
4. Add configuration to `pairs.ini`
5. Test with backtesting framework

Example:
```python
from trading.strategies.base.strategy_macd_base import TradingStrategyMACD
from trading.dom.trade import Trade_Action

class TradingStrategy(TradingStrategyMACD):
    def check_if_need_open_trade(self, trading_time) -> Trade_Action:
        # Your entry logic here
        if self.your_condition:
            return Trade_Action(trading_time, self.instrument, 
                              self.units_to_trade, self.ask, True, False, False)
```

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

[Specify your license here]

## Support

For issues and questions:
- Open an issue on GitHub
- Check existing documentation in `IMPROVEMENTS_APPLIED.md`
- Review logs in `logs/trading/`

## Changelog

### v2.0 (2026-01-25)
- Added thread safety for concurrent trading
- Implemented position reconciliation
- Optimized DataFrame operations (4x faster)
- Improved error handling
- Fixed duration calculation bug
- Added comprehensive documentation

### v1.0
- Initial release
- MACD and Mean Reversion strategies
- OANDA API integration
- Backtesting framework
- AWS deployment support

---

**Built with Python 🐍 | Powered by OANDA 📈 | Deployed on AWS ☁️**
