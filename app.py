import warnings
from urllib3.exceptions import NotOpenSSLWarning

warnings.filterwarnings("ignore", category=NotOpenSSLWarning)

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
MESSAGES_FILE = 'messages.json'
CHANNEL_IDENTIFIER = "-1001992580367"  # The channel to listen to
TARGET_CHANNEL_IDENTIFIER = "-1001234567890"  # The channel to send messages to
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

def pair_prices(data):
    entry = None
    result = []

    for item in data:
        if 'text' in item and isinstance(item['text'], str):  # Ensure 'text' is a string
            entry_price_match = re.search(r'Actual price: (\d+\.\d+)', item['text'])
            exit_price_match = re.search(r'price is (?:UP to|DOWN to) (\d+\.\d+)', item['text'])

            if entry_price_match:
                entry = {
                    'id': item['id'],
                    'entry_time': int(datetime.fromisoformat(item['date'].replace('Z', '+00:00')).timestamp()),
                    'entry_price': float(entry_price_match.group(1))
                }
            elif exit_price_match and entry:
                prediction_match = re.search(r'(✅|❌)', item['text'])
                direction_match = re.search(r'(↗️|↘️)', item['text'])

                if prediction_match and direction_match:
                    prediction = prediction_match.group(1)
                    direction = direction_match.group(1)
                    
                    if (prediction == '❌' and direction == '↘️') or (prediction == '✅' and direction == '↗️'):
                        side = 'LONG'
                    elif (prediction == '❌' and direction == '↗️') or (prediction == '✅' and direction == '↘️'):
                        side = 'SHORT'
                    else:
                        side = 'UNKNOWN'
                    
                    result.append({
                        'id': entry['id'],
                        'entry_time': entry['entry_time'],
                        'entry_price': entry['entry_price'],
                        'exit_price': float(exit_price_match.group(1)),
                        'exit_time': int(datetime.fromisoformat(item['date'].replace('Z', '+00:00')).timestamp()),
                        'exit_id': item['id'],
                        'side': side
                    })
                    entry = None  # Reset entry after pairing

    return result

async def fetch_all_messages(client, channel):
    all_messages = []
    last_id = 0
    batch_size = 100

    while True:
        messages = await client.get_messages(channel, limit=batch_size, offset_id=last_id)
        if not messages:
            break
        all_messages.extend(messages)
        last_id = messages[-1].id
        await asyncio.sleep(1)  # Add delay to comply with rate limits

    # Extract plain text and relevant information
    messages_data = []
    for message in all_messages:
        messages_data.append({
            'id': message.id,
            'date': message.date.isoformat(),
            'text': message.message
        })

    # Save to messages.json
    with open('messages.json', 'w') as f:
        json.dump(messages_data, f, indent=4)

    return all_messages

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
    target_channel_identifier = TARGET_CHANNEL_IDENTIFIER

    if channel_identifier.startswith('-100'):
        channel_identifier = int(channel_identifier)
    
    if target_channel_identifier.startswith('-100'):
        target_channel_identifier = int(target_channel_identifier)

    try:
        channel = await client.get_entity(channel_identifier)
        target_channel = await client.get_entity(target_channel_identifier)
    except ValueError as e:
        print(f"Error: {e}")
        return
    except errors.rpcerrorlist.UsernameInvalidError:
        print(f"Error: The username {channel_identifier} is invalid.")
        return
    except Exception as e:
        print(f"Unexpected error: {e}")
        return

    if os.path.exists(MESSAGES_FILE):
        print(f"{MESSAGES_FILE} already exists. Loading messages from file.")
        with open(MESSAGES_FILE, 'r') as f:
            all_messages = json.load(f)
    else:
        all_messages = await fetch_all_messages(client, channel)
        with open(MESSAGES_FILE, 'w') as f:
            json.dump(all_messages, f, indent=4)

    trades = pair_prices(all_messages)  # Use pair_prices here
    save_trades(trades)
    print(f"Trades have been saved to {TRADES_FILE}")

    print("Event handler is now listening for new messages...")

    @client.on(events.NewMessage(chats=channel_identifier))
    async def new_message_listener(event):
        message = event.message.message
        message_data = {
            'id': event.message.id,
            'date': event.message.date.isoformat(),
            'text': event.message.message
        }
        all_messages.append(message_data)
        trades = pair_prices(all_messages)  # Use pair_prices here
        save_trades(trades)
        print(f"Updated trades have been saved to {TRADES_FILE}")
        print("New message received and processed")
        
        # Send a message to the target channel
        await client.send_message(target_channel, f"New message processed: {message}")

    await client.run_until_disconnected()

async def plot_candles_task():
    await asyncio.sleep(5)  # Wait for some time to ensure the main loop is running
    fetch_and_plot_candles()

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
    try:
        response.raise_for_status()
        data = response.json()
        if data:
            print(f"Fetched {len(data)} candles for symbol {symbol} from {start_time} to {end_time}")
        else:
            print(f"No data returned for symbol {symbol} from {start_time} to {end_time}")
        return data
    except requests.exceptions.HTTPError as err:
        print(f"HTTP error occurred: {err}")
    except Exception as err:
        print(f"Other error occurred: {err}")
    return []

def fetch_all_candles(symbol, interval, start_time, end_time):
    all_candles = []
    current_start_time = start_time
    request_interval = 2.5

    interval_mapping = {
        '1m': 1,
        '3m': 3,
        '5m': 5,
        '15m': 15,
        '30m': 30,
        '1h': 60,
        '2h': 2 * 60,
        '4h': 4 * 60,
        '6h': 6 * 60,
        '8h': 8 * 60,
        '12h': 12 * 60,
        '1d': 24 * 60,
        '3d': 3 * 24 * 60,
        '1w': 7 * 24 * 60,
        '1M': 30 * 24 * 60
    }

    if interval not in interval_mapping:
        raise ValueError("Invalid interval provided")

    interval_min = interval_mapping[interval]
    total_duration = (end_time - start_time) / 60000
    num_candles = total_duration // interval_min
    num_batches = (num_candles + 1499) // 1500

    print(f"Fetching {num_batches} batches of candles...")
    estimated_time = num_batches * request_interval / 60
    print(f"Estimated time to fetch all candles: {estimated_time:.2f} minutes")

    while current_start_time < end_time:
        candles = fetch_candles(symbol, interval, current_start_time, end_time)
        if not candles:
            print(f"No candles fetched for start time {current_start_time}")
            break
        print(f"Fetched {len(candles)} candles for start time {current_start_time}")
        all_candles.extend(candles)
        current_start_time = candles[-1][0] + 1
        time.sleep(request_interval)

    if not all_candles:
        print("No candles were fetched.")
    else:
        print(f"Total fetched candles: {len(all_candles)}")

    return all_candles

def save_candles(candles):
    if candles:
        with open(CANDLES_FILE, 'w') as f:
            json.dump(candles, f, indent=4)
        print(f"Saved {len(candles)} candles to {CANDLES_FILE}")
    else:
        print("No candles to save.")

def load_candles():
    if os.path.exists(CANDLES_FILE):
        with open(CANDLES_FILE, 'r') as f:
            return json.load(f)
    return []

def plot_candles_with_trades(candles, trades, symbol, interval):
    if not candles:
        print("No candles to plot.")
        return

    candles = candles[-1000:]

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

    start_time = times[0]
    end_time = times[-1]

    relevant_trades = [trade for trade in trades if start_time <= datetime.fromtimestamp(trade['entry_time']) <= end_time]

    for trade in relevant_trades:
        entry_time = datetime.fromtimestamp(trade['entry_time'])
        exit_time = datetime.fromtimestamp(trade['exit_time'])
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

def fetch_and_plot_candles():
    trades = load_trades()
    if trades:
        entry_time = trades[0]['entry_time']
        exit_time = trades[-1]['exit_time']
        symbol = 'BTCUSDT'
        interval = '5m'

        if not os.path.exists(CANDLES_FILE):
            candles = fetch_all_candles(symbol, interval, entry_time, exit_time)
            save_candles(candles)
        else:
            candles = load_candles()

        plot_candles_with_trades(candles, trades, symbol, interval)

if __name__ == "__main__":
    api_id, api_hash = load_credentials()
    if not api_id or not api_hash:
        api_id, api_hash = get_credentials()
        save_credentials(api_id, api_hash)

    client = TelegramClient(SESSION_FILE, api_id, api_hash)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(main(), plot_candles_task()))
