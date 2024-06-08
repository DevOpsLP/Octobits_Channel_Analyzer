import csv
import json
import os
from datetime import datetime

# Constants
INITIAL_INVESTMENT = 1000  # Initial investment in USDT
INVESTMENT_PERCENTAGE = 0.1  # Percentage of the initial investment to use for each trade
LEVERAGE = 20  # Leverage for futures trading
TRADE_FEE_PERCENTAGE_MAKER = 0.02  # Maker fee percentage
TRADE_FEE_PERCENTAGE_TAKER = 0.02  # Taker fee percentage (we'll assume maker fee for simplicity)

# Load trades
def load_trades():
    if os.path.exists(TRADES_FILE):
        with open(TRADES_FILE, 'r') as f:
            return json.load(f)
    return []

# Calculate trade PnL and fees
def calculate_trade_pnl(trade):
    entry_price = trade['entry_price']
    exit_price = trade['exit_price']
    side = trade['side']

    # Calculate the quantity based on leverage and investment percentage
    amount_to_invest = INITIAL_INVESTMENT * INVESTMENT_PERCENTAGE
    quantity = round((amount_to_invest * LEVERAGE) / entry_price, 6)

    if side == 'LONG':
        pnl = (exit_price - entry_price) * quantity
    elif side == 'SHORT':
        pnl = (entry_price - exit_price) * quantity
    else:
        pnl = 0

    # Calculate fees
    leveraged_position = amount_to_invest * LEVERAGE
    fee = (leveraged_position / 100) * TRADE_FEE_PERCENTAGE_MAKER

    # Final PnL after fees
    final_pnl = pnl - fee
    return final_pnl

# Calculate total and monthly earnings
def calculate_earnings(trades):
    total_earnings = 0
    monthly_earnings = {}
    monthly_drawdowns = {}
    balance = INITIAL_INVESTMENT
    peak_balance = balance

    for trade in trades:
        trade_pnl = calculate_trade_pnl(trade)
        total_earnings += trade_pnl
        balance += trade_pnl

        # Ensure the exit_time is correctly converted to a timestamp
        try:
            trade_date = datetime.fromtimestamp(trade['exit_time'])
        except ValueError as e:
            print(f"Error converting timestamp for trade ID {trade['id']}: {e}")
            continue

        month_key = trade_date.strftime('%Y-%m')
        if month_key not in monthly_earnings:
            monthly_earnings[month_key] = 0
            monthly_drawdowns[month_key] = {'drawdown': 0, 'peak_balance': peak_balance}

        monthly_earnings[month_key] += trade_pnl

        # Update peak balance and drawdown for the month
        if balance > monthly_drawdowns[month_key]['peak_balance']:
            monthly_drawdowns[month_key]['peak_balance'] = balance

        drawdown = monthly_drawdowns[month_key]['peak_balance'] - balance
        if drawdown > monthly_drawdowns[month_key]['drawdown']:
            monthly_drawdowns[month_key]['drawdown'] = drawdown

    return total_earnings, monthly_earnings, {k: v['drawdown'] for k, v in monthly_drawdowns.items()}

# Generate CSV report
def generate_csv_report(monthly_earnings, monthly_drawdowns, total_earnings):
    with open('trading_report.csv', 'w', newline='') as csvfile:
        fieldnames = ['Month', 'Earnings (USDT)', 'Max Drawdown (USDT)']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for month, earnings in sorted(monthly_earnings.items()):
            drawdown = monthly_drawdowns.get(month, 0)
            writer.writerow({'Month': month, 'Earnings (USDT)': earnings, 'Max Drawdown (USDT)': drawdown})

        writer.writerow({'Month': 'Total', 'Earnings (USDT)': total_earnings, 'Max Drawdown (USDT)': ''})

# Display results on console
def display_results(total_earnings, monthly_earnings, monthly_drawdowns):
    print(f"Initial Investment: {INITIAL_INVESTMENT} USDT")
    print(f"Total Earnings: {total_earnings:.2f} USDT")
    print(f"Total ROI: {(INITIAL_INVESTMENT + total_earnings) / INITIAL_INVESTMENT * 100 - 100:.2f}%")

    for month, earnings in sorted(monthly_earnings.items()):
        drawdown = monthly_drawdowns.get(month, 0)
        print(f"Earnings for {month}: {earnings:.2f} USDT, Max Drawdown: {drawdown:.2f} USDT")

# Main function to process trades and generate report
def main():
    trades = load_trades()
    total_earnings, monthly_earnings, monthly_drawdowns = calculate_earnings(trades)
    generate_csv_report(monthly_earnings, monthly_drawdowns, total_earnings)
    display_results(total_earnings, monthly_earnings, monthly_drawdowns)

if __name__ == "__main__":
    TRADES_FILE = 'trades.json'
    main()
