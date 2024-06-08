import json
import os
from telethon import TelegramClient, errors
import asyncio

CONFIG_FILE = 'config.json'
SESSION_FILE = 'session.session'
CHANNEL_IDENTIFIER = "-1001992580367"

# Function to load credentials from the config file
def load_credentials():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            data = json.load(f)
            return data['api_id'], data['api_hash']
    return None, None

# Function to save credentials to the config file
def save_credentials(api_id, api_hash):
    with open(CONFIG_FILE, 'w') as f:
        json.dump({'api_id': api_id, 'api_hash': api_hash}, f)

# Function to fetch a specific message by its ID
async def fetch_message_by_id(client, channel, message_id):
    try:
        message = await client.get_messages(channel, ids=message_id)
        return message
    except errors.RPCError as e:
        print(f"An error occurred: {e}")
        return None

async def main():
    api_id, api_hash = load_credentials()
    if not api_id or not api_hash:
        api_id = input('Enter your API ID: ')
        api_hash = input('Enter your API Hash: ')
        save_credentials(api_id, api_hash)

    client = TelegramClient(SESSION_FILE, api_id, api_hash)
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

    # Fetch specific messages by ID
    message_ids = [6, 7]
    for message_id in message_ids:
        message = await fetch_message_by_id(client, channel, message_id)
        if message:
            print(f"Message ID {message_id}:")
            print(f"Text: {message.text}")
            print(f"Date: {message.date}")
            print(f"ID: {message.id}")
        else:
            print(f"Message ID {message_id} could not be fetched.")

if __name__ == "__main__":
    asyncio.run(main())