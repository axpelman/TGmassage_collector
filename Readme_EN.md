```markdown
# Telegram Message Collector

A tool for collecting messages from Telegram channels/chats with date filtering capabilities.

## 📌 Features

- Connect to Telegram channels and chats
- Collect messages within a specified time period
- Automatic saving to text files
- Support for private channels (with access)
- Russian/English localization

## ⚙️ Installation

1. Ensure you have Python 3.8+ installed
2. Install dependencies:
   ```bash
   pip install telethon pytz configparser
   ```
3. Create a `config.ini` file in the same directory with the following content:
   ```ini
   [Telegram]
   api_id = your_api_id
   api_hash = your_api_hash
   phone = your_phone_number
   ```

## 🔐 Obtaining API Keys

1. Go to [my.telegram.org](https://my.telegram.org/)
2. Create a new application (App)
3. Get your `api_id` and `api_hash`

## 🚀 Usage

1. Run the script:
   ```bash
   python telegram_collector.py
   ```
2. On first run, enter the verification code from Telegram
3. Enter channel/chat parameters:
   - Group ID (starts with -100)
   - Invite link (e.g., `https://t.me/joinchat/ABCDEF12345`)
   - @username (for public channels)
4. Specify the time range for message collection

## 🔗 Connecting to Channels/Chats

### For public channels:
- Use channel @username (e.g., `@channel_name`)
- Or full link (e.g., `https://t.me/channel_name`)

### For private channels:
1. Get an invite link from admin
2. Use link in format `https://t.me/joinchat/ABCDEF12345`
3. Or channel ID (starts with -100...)

### For supergroups:
- Use group ID (starts with -100)

## 📂 Output Format

Messages are saved in the `Collected_messages` folder in format:
```
[date]
message text
```

Files are named by collection date: `messages_YYYY-MM-DD_HH-MM-SS.txt`

## ⚠️ Limitations

- For private channels, your account must be a member
- Telegram API has request limits
- Collection may take significant time for very large channels

## 📜 License

MIT License
```

Key improvements in the English version:
1. More concise technical language
2. Standardized terminology (e.g., "channels/chats" instead of mixing terms)
3. Removed culture-specific references
4. Simplified installation instructions
5. Clearer formatting for code blocks and headers

