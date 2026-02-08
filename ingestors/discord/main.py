import discord
import asyncio
import xml.etree.ElementTree as ET
import datetime
import logging

from common import load_config, IngestAPIClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CONFIG = load_config()

# Initialize the IngestAPIClient with configurations
INGEST_CLIENT = IngestAPIClient(CONFIG.ingestion_endpoint, CONFIG.ingestion_api_key)

# Initialize Discord client with appropriate intents
intents = discord.Intents.default()
intents.message_content = True  # Required to read message content
intents.guild_messages = True   # Required for messages in guilds
intents.guilds = True           # Required for guild information
client = discord.Client(intents=intents)

message_buffer = []
message_buffer_lock = asyncio.Lock()

async def process_message_batch():
    """Processes the buffered messages, constructs an XML payload, and sends it for ingestion."""
    global message_buffer
    if not message_buffer:
        return

    root = ET.Element("discord_messages")
    metadata_elem = ET.SubElement(root, "metadata")
    ET.SubElement(metadata_elem, "batch_size").text = str(len(message_buffer))
    ET.SubElement(metadata_elem, "timestamp").text = datetime.datetime.now().isoformat()

    messages_elem = ET.SubElement(root, "messages")
    for msg in message_buffer:
        message_elem = ET.SubElement(messages_elem, "message")
        ET.SubElement(message_elem, "id").text = str(msg.id)
        ET.SubElement(message_elem, "author_id").text = str(msg.author.id)
        ET.SubElement(message_elem, "author_name").text = str(msg.author)
        ET.SubElement(message_elem, "channel_id").text = str(msg.channel.id)
        ET.SubElement(message_elem, "channel_name").text = str(msg.channel.name)
        if msg.guild:
            ET.SubElement(message_elem, "guild_id").text = str(msg.guild.id)
            ET.SubElement(message_elem, "guild_name").text = str(msg.guild.name)
        ET.SubElement(message_elem, "created_at").text = msg.created_at.isoformat()
        content_elem = ET.SubElement(message_elem, "content")
        content_elem.text = msg.content

    xml_payload = ET.tostring(root, encoding="unicode", xml_declaration=True)

    try:
        logging.info(f"Sending batch of {len(message_buffer)} messages for ingestion.")
        ingestion_response = await INGEST_CLIENT.ingest(xml_payload)
        logging.info(f"Ingestion successful: {ingestion_response}")

        message_buffer = [] # Clear buffer after attempt
    except Exception as e:
        logging.error(f"Failed to ingest message batch: {e}")

@client.event
async def on_ready():
    """Called when the bot is ready and connected to Discord."""
    logging.info(f'Logged in as {client.user}')
    if CONFIG.monitor_all_channels:
        logging.info("Monitoring all accessible channels.")
    else:
        logging.info(f'Monitoring specific channels: {CONFIG.discord_channel_ids}')
    client.loop.create_task(flush_buffer_periodically())

@client.event
async def on_message(message):
    """Processes incoming Discord messages."""
    # Ignore messages from the bot itself
    if message.author == client.user:
        return

    # Only process messages from configured channels if not monitoring all channels
    if not CONFIG.monitor_all_channels and str(message.channel.id) not in [str(c_id) for c_id in CONFIG.discord_channel_ids]:
        return

    logging.info(f"Received message (ID: {message.id}) from {message.author} (ID: {message.author.id}) in #{message.channel.name} (Channel ID: {message.channel.id})"
                 f"{f' in Guild: {message.guild.name} (ID: {message.guild.id})' if message.guild else ''}: {message.content[:100]}...")

    async with message_buffer_lock:
        message_buffer.append(message)
        if len(message_buffer) >= CONFIG.message_batch_size:
            await process_message_batch()

async def flush_buffer_periodically():
    """Flushes the message buffer periodically, in case batches don't fill up quickly."""
    while True:
        await asyncio.sleep(CONFIG.sleep_delay)  # Flush every 60 seconds
        async with message_buffer_lock:
            if message_buffer:
                logging.info("Flushing message buffer due to periodic timer.")
                await process_message_batch()

async def main_async():
    """Main asynchronous function to start the Discord bot and background tasks."""
    try:

        await client.start(CONFIG.discord_bot_token)
    except Exception as e:
        logging.error(f"Error running Discord bot: {e}")

if __name__ == "__main__":
    if not CONFIG.discord_bot_token or CONFIG.discord_bot_token == "YOUR_DISCORD_BOT_TOKEN_HERE":
        logging.error("Discord bot token not configured. Please update ingestors/discord/config.yaml")
    elif not CONFIG.monitor_all_channels and not CONFIG.discord_channel_ids:
        logging.warning("No Discord channel IDs configured and 'monitor_all_channels' is false. The bot will not ingest any messages. Please configure channels or set 'monitor_all_channels' to true in ingestors/discord/config.yaml.")
    else:
        asyncio.run(main_async())