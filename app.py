import os
import json
import re
import time
import requests
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from telethon import TelegramClient, events, errors
import asyncio

CONFIG_FILE = 'config.json'
SESSION_FILE = 'session.session'
TRADES_FILE = 'trades.json'
CANDLES_FILE = 'candles.json'
CHANNEL_IDENTIFIER = "-1001992580367"
BINANCE_API_URL = 'https://fapi.binance.com/fapi/v1/klines'

def get_credentials():
    api_id = input('Enter your API ID: ')
    api_hash = input('Enter your API Hash: ')
    return api_id, api_hash

def save_credentials(api_id, api_hash):
    with open(CONFIG_FILE, 'w') as f:
        json.dump({'api_id': api_id, 'api_hash': api_hash}, f)

def load_credentials():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            data = json.load(f)
            return data['api_id'], data['api_hash']
    return None, None

def save_trades(trades):
    with open(TRADES_FILE, 'w') as f:
        json.dump(trades, f, indent=4)

def load_trades():
    if os.path.exists(TRADES_FILE):
        with open(TRADES_FILE, 'r') as f:
            return json.load(f)
    return []

def parse_message(message):
    entry_price_pattern = re.compile(r'Actual price:\s([\d.]+)\sUSDT/BTC')
    result_pattern = re.compile(r'(❌|✅) Prediction was (unsuccessful|successful)\.\n(↘️|↗️) price is (DOWN|UP) to ([\d.]+)\n(Loss|Profit) of trade is: ([\d.]+) %')

    entry_price_match = entry_price_pattern.search(message)
    result_match = result_pattern.search(message)

    if entry_price_match:
        entry_price = float(entry_price_match.group(1))
        return {'entry_price': entry_price}

    if result_match:
        prediction = result_match.group(1)
        direction = result_match.group(3)
        exit_price = float(result_match.group(5))
        side = None

        if (prediction == '❌' and direction == '↘️') or (prediction == '✅' and direction == '↗️'):
            side = 'LONG'
        elif (prediction == '❌' and direction == '↗️') or (prediction == '✅' and direction == '↘️'):
            side = 'SHORT'

        return {'exit_price': exit_price, 'side': side}

    return None

async def fetch_all_messages(client, channel):
    all_messages = []
    last_id = 0
    while True:
        messages = await client.get_messages(channel, limit=100, offset_id=last_id)
        if not messages:
            break
        all_messages.extend(messages)
        last_id = messages[-1].id
        await asyncio.sleep(0.1)  # Add delay to comply with rate limits
    return all_messages

async def process_messages(messages):
    trades = []
    entry_data = None
    for message in reversed(messages):  # Reverse to maintain order from oldest to newest
        if message.text:
            parsed_data = parse_message(message.text)
            if parsed_data:
                timestamp = int(message.date.timestamp() * 1000)  # Convert to milliseconds
                if 'entry_price' in parsed_data:
                    entry_data = parsed_data
                    entry_data['entry_time'] = timestamp  # Store entry time in milliseconds
                elif 'exit_price' in parsed_data and entry_data:
                    trade = {
                        'entry_price': entry_data['entry_price'],
                        'exit_price': parsed_data['exit_price'],
                        'side': parsed_data['side'],
                        'entry_time': entry_data['entry_time'],
                        'exit_time': timestamp  # Store exit time in milliseconds
                    }
                    trades.append(trade)
                    entry_data = None  # Reset entry data after storing trade
    return trades

async def main():
    await client.start()

    if not await client.is_user_authorized():
        phone_number = input('Enter your phone number: ')
        await client.send_code_request(phone_number)
        code = input('Enter the code: ')
        try:
            await client.sign_in(phone_number, code)
        except errors.SessionPasswordNeededError:
            password = input('2FA is enabled. Please enter your password: ')
            await client.sign_in(password=password)

    channel_identifier = CHANNEL_IDENTIFIER

    if channel_identifier.startswith('-100'):
        channel_identifier = int(channel_identifier)

    try:
        channel = await client.get_entity(channel_identifier)
    except ValueError as e:
        print(f"Error: {e}")
        return
    except errors.rpcerrorlist.UsernameInvalidError:
        print(f"Error: The username {channel_identifier} is invalid.")
        return
    except Exception as e:
        print(f"Unexpected error: {e}")
        return

    if os.path.exists(TRADES_FILE):
        print(f"{TRADES_FILE} already exists. Skipping message fetching.")
        trades = load_trades()
    else:
        all_messages = await fetch_all_messages(client, channel)
        trades = await process_messages(all_messages)
        save_trades(trades)
        print(f"Trades have been saved to {TRADES_FILE}")

    @client.on(events.NewMessage(chats=channel_identifier))
    async def new_message_listener(event):
        message = event.message.message
        parsed_data = parse_message(message)
        trades = load_trades()

        if parsed_data:
            timestamp = int(event.message.date.timestamp() * 1000)  # Convert to milliseconds
            if 'entry_price' in parsed_data:
                entry_data = parsed_data
                entry_data['entry_time'] = timestamp  # Store entry time in milliseconds
                trades.insert(0, entry_data)  # Insert at the beginning to maintain order
            elif 'exit_price' in parsed_data and trades:
                for trade in trades:
                    if 'exit_price' not in trade:
                        trade['exit_price'] = parsed_data['exit_price']
                        trade['side'] = parsed_data['side']
                        trade['exit_time'] = timestamp  # Store exit time in milliseconds
                        break

            save_trades(trades)
            print(f"Updated trades have been saved to {TRADES_FILE}")

    await client.run_until_disconnected()

def fetch_candles(symbol, interval, start_time, end_time):
    url = BINANCE_API_URL
    params = {
        'symbol': symbol,
        'interval': interval,
        'startTime': start_time,
        'endTime': end_time,
        'limit': 1500
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

def fetch_all_candles(symbol, interval, start_time, end_time):
    all_candles = []
    current_start_time = start_time

    while current_start_time < end_time:
        candles = fetch_candles(symbol, interval, current_start_time, end_time)
        if not candles:
            break
        all_candles.extend(candles)
        current_start_time = candles[-1][0] + 1
        time.sleep(2.5)  # Add delay to comply with rate limits

    return all_candles

def save_candles(candles):
    with open(CANDLES_FILE, 'w') as f:
        json.dump(candles, f, indent=4)

def load_candles():
    if os.path.exists(CANDLES_FILE):
        with open(CANDLES_FILE, 'r') as f:
            return json.load(f)
    return []

def plot_candles_with_trades(candles, trades):
    times = [datetime.fromtimestamp(c[0] / 1000) for c in candles]
    opens = [float(c[1]) for c in candles]
    highs = [float(c[2]) for c in candles]
    lows = [float(c[3]) for c in candles]
    closes = [float(c[4]) for c in candles]

    fig, ax = plt.subplots()

    for i in range(len(times)):
        color = 'green' if closes[i] >= opens[i] else 'red'
        ax.plot([times[i], times[i]], [lows[i], highs[i]], color='black')
        ax.plot([times[i], times[i]], [opens[i], closes[i]], color=color, linewidth=4)

    for trade in trades:
        entry_time = datetime.fromtimestamp(trade['entry_time'] / 1000)
        exit_time = datetime.fromtimestamp(trade['exit_time'] / 1000)
        ax.annotate('Entry', xy=(entry_time, trade['entry_price']), xytext=(entry_time, trade['entry_price'] + 0.01),
                    arrowprops=dict(facecolor='blue', shrink=0.05))
        ax.annotate('Exit', xy=(exit_time, trade['exit_price']), xytext=(exit_time, trade['exit_price'] + 0.01),
                    arrowprops=dict(facecolor='red', shrink=0.05))
        ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=30))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        plt.xticks(rotation=45)
        plt.xlabel('Time')
        plt.ylabel('Price')
        plt.title(f'{symbol} {interval} Candles with Trades')
        plt.grid(True)
        plt.show()
# Create the Telegram client
api_id, api_hash = load_credentials()
if not api_id or not api_hash:
    api_id, api_hash = get_credentials()
    save_credentials(api_id, api_hash)

# Create the Telegram client
client = TelegramClient(SESSION_FILE, api_id, api_hash)

# Run the main function
with client:
    client.loop.run_until_complete(main())

# Fetch and plot candles if trades.json exists
if os.path.exists(TRADES_FILE):
    trades = load_trades()
    if trades:
        entry_time = trades[-1]['entry_time']
        exit_time = trades[0]['exit_time']
        symbol = 'BTCUSDT'  # Example symbol, adjust as needed
        interval = '5m'  # Example interval, adjust as needed

        if not os.path.exists(CANDLES_FILE):
            candles = fetch_all_candles(symbol, interval, entry_time, exit_time)
            save_candles(candles)
        else:
            candles = load_candles()

        plot_candles_with_trades(candles, trades)