# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

import email
import imaplib
import email.header
import json
import discord


class MailContent:
    def __init__(self):
        self.subject = ""
        self.sender = ""
        self.message = []

def login_to_imap_with_config(file_path):
    with open(file_path, 'r') as conf_file:
        config = json.load(conf_file)
        imap_server = imaplib.IMAP4_SSL(host=config["imap_server"])
        imap_server.login(config["emailAddress"], config["password"])
    return imap_server

def get_channel_id(file_path):
    channel_id = 0
    with open(file_path, 'r') as conf_file:
        config = json.load(conf_file)
        channel_id = int(config["channel_id"])
    return channel_id

def initialize_bot(file_path):
    bot_token = ""
    with open(file_path, 'r') as conf_file:
        config = json.load(conf_file)
        bot_token = config["bot_token"]
    if (bot_token == ""):
        print("ERROR: Config file doesn't seem to contain info about token")
        return
    client = discord.Client()

    # Kinda ugly solution but it works
    # Bot is constantly
    @client.event
    async def on_ready():
        while (True):
            imap = login_to_imap_with_config(config_file)

            channel_id = get_channel_id(config_file)
            if (channel_id == 0):
                continue

            channel = client.get_channel(channel_id)
            unseen_messages = find_unseen_in_inbox(imap)
            new_mails_to_print = []
            for message_id in unseen_messages[0].split():
                mail = handle_mail(message_id, imap)
                set_mail_as_seen(imap, message_id)
                if (len(mail.message) != 0):
                    new_mails_to_print.append(mail)

            for new_mail in new_mails_to_print:
                await channel.send("Email from: " + new_mail.sender)
                await channel.send("Subject: " + new_mail.subject)
                for mess in new_mail.message:
                    await channel.send(mess)

    client.run(config["bot_token"])

def get_list_mailboxes(imap_server):
    response_code, folders = imap_server.list()
    folder_details = []
    if response_code == "OK":
        print('Available folders(mailboxes) to select:')
        for folder_details_raw in folders:
            folder_details.append(folder_details_raw.decode().split()[-1])
    else:
        print("Cannot get list of mailboxes mailboxes, response is: ", response_code)
    return folder_details

def find_unseen_in_inbox(imap_server):
    select_status, amount_messages = imap_server.select("INBOX")
    # Amount of messages
    # int(amount_messages[0])
    if select_status != 'OK':
        print("ERROR: Could not open INBOX")
    search_status, unread_indexes = imap_server.search(None, '(UNSEEN)')
    if search_status != 'OK':
        print("ERROR: Could not search unseen messages")
    return unread_indexes

def handle_subject_and_sender(content):
    subject, subject_encoding = email.header.decode_header(content["Subject"])[0]
    if isinstance(subject, bytes):
        subject = subject.decode(subject_encoding)
    sender, sender_encoding = email.header.decode_header(content["From"])[0]
    if isinstance(sender, bytes):
        sender = sender.decode(sender_encoding)
    return subject, sender


def handle_mail(id, imap_server):
    status, mail = imap_server.fetch(id, '(RFC822)')
    if status != 'OK':
        print("ERROR: Could fetch mail with id: ", id, ". Response is: ", status)
        return
    mail_response = MailContent()
    for response_part in mail:
        # Dumb condition, because response may not fit in one bytestream so it is as array,
        # lets hope it won't make and complications. Maybe it has different reason.
        if isinstance(response_part, tuple):
            mail_content = email.message_from_bytes(response_part[1])
            # Get Subject and sender of mail
            sender, subject = handle_subject_and_sender(mail_content)
            mail_response.sender = sender
            mail_response.subject = subject
            # Multipart is either resended mail or response to mail, or it may just contain attachment or some formatting.
            if mail_content.is_multipart():
                for part in mail_content.walk():
                    # Get content type and it's conetent
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    try:
                        part_body = part.get_payload(decode=True).decode()
                    except:
                        continue
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        mail_response.message.append(part_body)
                    # elif "attachment"  in content_disposition:
                    # TODO: Attachment doesn't have to be handled yet
                    #   Implement: handle_attachment() if needed
            else:
                content_type = mail_content.get_content_type()
                part_body = mail_content.get_payload(decode=True).decode()
                if content_type == "text/plain":
                    mail_response.message.append(part_body)

    return mail_response

def set_mail_as_seen(imap_server, id):
    status, data = imap_server.store(id, '+FLAGS','\\Seen')
    if status != "OK":
        print("ERROR: Could set mail with id: ", id, " as seen. Response is: ", status)




# Press the green button in the gutter to run the script.
if __name__ == '__main__':

    config_file = "config.json"
    discord_bot = initialize_bot(config_file)


