import imapclient
import ssl
import email
import asyncio
import xml.etree.ElementTree as ET
import datetime
import logging
from html2text import html2text

from common import load_config, IngestAPIClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CONFIG = load_config()

# Initialize the IngestAPIClient with configurations
INGEST_CLIENT = IngestAPIClient(CONFIG.ingestion_endpoint, CONFIG.ingestion_api_key)

email_buffer = []
email_buffer_lock = asyncio.Lock()

async def process_email_batch():
    """Processes the buffered emails, constructs an XML payload, and sends it for ingestion."""
    global email_buffer
    if not email_buffer:
        return

    root = ET.Element("emails")
    metadata_elem = ET.SubElement(root, "metadata")
    ET.SubElement(metadata_elem, "batch_size").text = str(len(email_buffer))
    ET.SubElement(metadata_elem, "timestamp").text = datetime.datetime.now().isoformat()

    emails_elem = ET.SubElement(root, "emails")
    for msg_data in email_buffer:
        msg_id = msg_data['id']
        parsed_msg = msg_data['parsed_msg']
        
        email_elem = ET.SubElement(emails_elem, "email")
        ET.SubElement(email_elem, "id").text = str(msg_id)
        ET.SubElement(email_elem, "from").text = parsed_msg.get("From", "N/A")
        ET.SubElement(email_elem, "to").text = parsed_msg.get("To", "N/A")
        ET.SubElement(email_elem, "subject").text = parsed_msg.get("Subject", "N/A")
        ET.SubElement(email_elem, "date").text = parsed_msg.get("Date", "N/A")

        body_elem = ET.SubElement(email_elem, "body")
        
        # Extract plain text body
        plain_text_body = ""
        html_body = ""
        for part in parsed_msg.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get("Content-Disposition"))

            if ctype == "text/plain" and "attachment" not in cdispo:
                plain_text_body = part.get_payload(decode=True).decode(errors='ignore')
                break # Prefer plain text if available
            elif ctype == "text/html" and "attachment" not in cdispo:
                html_body = part.get_payload(decode=True).decode(errors='ignore')
        
        if plain_text_body:
            body_elem.text = plain_text_body
        elif html_body:
            body_elem.text = html2text(html_body) # Convert HTML to markdown/text
        else:
            body_elem.text = "[No readable content]"


    xml_payload = ET.tostring(root, encoding="unicode", xml_declaration=True)

    try:
        logging.info(f"Sending batch of {len(email_buffer)} emails for ingestion.")
        ingestion_response = await INGEST_CLIENT.ingest(xml_payload)
        logging.info(f"Ingestion successful: {ingestion_response}")
    except Exception as e:
        logging.error(f"Failed to ingest email batch: {e}")
    finally:
        email_buffer = [] # Clear buffer after attempt


async def fetch_emails():
    """Connects to IMAP, fetches unread emails, and processes them."""
    context = ssl.create_default_context()
    if not CONFIG.imap_ssl:
        context = None # No SSL

    with imapclient.IMAPClient(CONFIG.imap_server, port=CONFIG.imap_port, ssl=CONFIG.imap_ssl, ssl_context=context) as client:
        logging.info(f"Connecting to IMAP server: {CONFIG.imap_server}:{CONFIG.imap_port}")
        try:
            client.login(CONFIG.username, CONFIG.password)
            logging.info(f"Logged in as {CONFIG.username}")
        except imapclient.exceptions.LoginError:
            logging.error("IMAP login failed. Check username and password.")
            return

        client.select_folder(CONFIG.mailbox)
        logging.info(f"Selected mailbox: {CONFIG.mailbox}")

        # Search for unread emails. Use 'ALL' to fetch all emails, then filter.
        messages = client.search('UNSEEN') 
        logging.info(f"Found {len(messages)} new emails.")

        if not messages:
            return

        # Fetch message data. 'RFC822' fetches the entire email body.
        # UID is used for persistent IDs, which is better for marking/moving
        response = client.fetch(messages, ['RFC822', 'UID'])

        for msg_uid, msg_data in response.items():
            raw_email = msg_data[b'RFC822']
            parsed_msg = email.message_from_bytes(raw_email)

            async with email_buffer_lock:
                email_buffer.append({'id': msg_uid, 'parsed_msg': parsed_msg})
                if len(email_buffer) >= CONFIG.email_batch_size:
                    await process_email_batch()
            
            if CONFIG.mark_as_read:
                client.set_flags(msg_uid, ['\Seen'])
                logging.debug(f"Marked email UID {msg_uid} as read.")
            
            if CONFIG.move_to_folder:
                if CONFIG.move_to_folder not in client.list_folders(): # Check if folder exists
                    logging.warning(f"Target folder '{CONFIG.move_to_folder}' does not exist. Creating it.")
                    client.create_folder(CONFIG.move_to_folder)
                client.move(msg_uid, CONFIG.move_to_folder)
                logging.debug(f"Moved email UID {msg_uid} to '{CONFIG.move_to_folder}'.")

        # Process any remaining emails in the buffer after the loop
        if email_buffer:
            await process_email_batch()


async def poll_emails_periodically():
    """Polls for new emails at a configured interval."""
    while True:
        await fetch_emails()
        logging.info(f"Waiting for {CONFIG.poll_interval_seconds} seconds before next email poll.")
        await asyncio.sleep(CONFIG.poll_interval_seconds)


async def main_async():
    """Main asynchronous function to start the email ingestor."""
    try:
        await poll_emails_periodically()
    except Exception as e:
        logging.error(f"Error in email ingestor: {e}")

if __name__ == "__main__":
    if not CONFIG.username or CONFIG.username == "your_email@example.com":
        logging.error("Email username not configured. Please update ingestors/email/config.yaml")
    elif not CONFIG.password or CONFIG.password == "your_email_password":
        logging.error("Email password not configured. Please update ingestors/email/config.yaml")
    else:
        logging.info("Starting email ingestor...")
        asyncio.run(main_async())
