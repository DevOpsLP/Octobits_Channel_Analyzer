# Telegram Channel Trade Analyzer

This project involves building a tool that extracts trade information from a specific Telegram channel, processes the trade data, and fetches corresponding candlestick data from the Binance API to visualize the trades on a chart. The tool includes functionalities for handling API rate limits, saving data locally, and ensuring efficient data retrieval.

## Features

1. **Telegram Client Initialization**: Connects to Telegram using user API credentials.
2. **Message Extraction**: Fetches all messages from a specified Telegram channel.
3. **Trade Parsing**: Parses messages to extract trade entry and exit information.
4. **Trade Storage**: Saves extracted trade data to `trades.json`.
5. **Candle Fetching**: Fetches candlestick data from Binance API based on trade times.
6. **Rate Limiting**: Ensures compliance with Binance API rate limits.
7. **Data Visualization**: Plots trades on a candlestick chart.

## Requirements

- Python 3.7+
- Telethon
- Requests
- Matplotlib

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/yourusername/telegram-trade-analyzer.git
    cd telegram-trade-analyzer
    ```

2. Install the required Python packages:
    ```bash
    pip install telethon requests matplotlib
    ```

3. Set up your Telegram API credentials:
    - Obtain your API ID and Hash from [my.telegram.org](https://my.telegram.org).
    - Create a `config.json` file with the following structure:
      ```json
      {
          "api_id": "YOUR_API_ID",
          "api_hash": "YOUR_API_HASH"
      }
      ```

## Usage

### Running the Script

1. Ensure your `config.json` file contains your Telegram API credentials.
2. Run the main script:
    ```bash
    python your_script.py
    ```

### What the Script Does

1. **Connects to Telegram**:
    - Initializes the Telegram client using API credentials from `config.json`.
    - Authenticates the user via a phone number and verification code if not already authenticated.

2. **Extracts Messages**:
    - Fetches all messages from the specified Telegram channel.
    - Processes each message to extract trade entry and exit information.

3. **Handles API Rate Limits**:
    - Binance API requests are rate-limited to 24 requests per minute (one request every 2.5 seconds) to comply with the 2400 weight per minute limit.

4. **Fetches Candlestick Data**:
    - Based on the entry and exit times of trades, fetches the required candlestick data from the Binance API.
    - Stores fetched candlestick data in `candles.json` to avoid redundant API calls.

5. **Plots Trades on Candlestick Chart**:
    - Visualizes the trades on a candlestick chart, marking the entry and exit points for each trade.

## File Descriptions

- **config.json**: Stores Telegram API credentials.
- **trades.json**: Stores extracted trade data with entry and exit details.
- **candles.json**: Stores fetched candlestick data from Binance.

## Rate Limiting Considerations

- **Binance API**: 
  - Limit of 2400 request weight per minute.
  - Each `/fapi/v1/klines` request has a weight of 10.
  - The script limits requests to 24 per minute (one every 2.5 seconds) to stay within the limit.

## Important Notes

- Ensure the Telegram API credentials are correct and have sufficient permissions to access the specified channel.
- The channel identifier must be valid and accessible by the user account.
- The script fetches and processes messages in batches to handle large volumes efficiently.
- Ensure the `trades.json` and `candles.json` files are writable and located in the script's directory.

## Example Visualization

After running the script, an example candlestick chart with marked trade entries and exits will be displayed, similar to the following:

![Example Chart](example_chart.png)

## Future Enhancements

- Add support for multiple timeframes for candlestick data.
- Implement error handling for network-related issues.
- Enhance visualization with more detailed trade annotations.

## Contributions

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.