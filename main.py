# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

import email
import imaplib
import email.header
import email.utils
import json
import ssl
import discord
import os

class MailContent:
    def __init__(self):
        self.subject = ""
        self.sender = ""
        self.sender_address = ""
        self.receiver_address = ""
        self.message = []


def get_var(name):
    return os.getenv(name)

def get_var(file_path, name):
    if file_path == "":
        return get_var(name)
    with open(file_path, 'r') as conf_file:
        config = json.load(conf_file)
        return config[name]


def login_to_imap_with_config(file_path):
    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    imap_server = imaplib.IMAP4(host=get_var(file_path, "imap_server"), port=int(get_var(file_path,"imap_port")))
    imap_server.starttls(context)
    imap_server.login(get_var(file_path,"emailAddress"), get_var(file_path,"password"))
    return imap_server

def get_white_list(file_path):
    white_list = get_var(file_path, "white_list")
    split_list = white_list.replace("[", "").replace("]", "").strip().split(";")
    parsed_white = []
    for splitted in split_list:
        parsed_split = splitted.replace("(", "").replace(")", "").strip().split(",")
        parsed_white.append((parsed_split[0].strip(), parsed_split[1].strip()))
    return parsed_white


def initialize_bot(file_path):
    client = discord.Client()

    # Kinda ugly solution but it works
    # Bot is constantly waiting for new mails, periodic check would be better.
    @client.event
    async def on_ready():
        while (True):
            imap = login_to_imap_with_config(config_file)


            unseen_messages = find_unseen_in_inbox(imap)
            new_mails_to_print = []
            for message_id in unseen_messages[0].split():
                mail = handle_mail(message_id, imap)
                set_mail_as_seen(imap, message_id)
                if (len(mail.message) != 0):
                    new_mails_to_print.append(mail)

            for new_mail in new_mails_to_print:
                white_list = get_white_list(file_path)
                for white_list_el in white_list:
                    if (new_mail.receiver_address.strip() == white_list_el[0].strip()):
                        channel = client.get_channel(int(white_list_el[1]))
                        to_sent = "Email from: __**" + new_mail.sender + "**__\n"
                        to_sent += "Subject: __**" + new_mail.subject + "**__\n\n"

                        for mess in new_mail.message:
                            to_sent += mess + "\n"
                        send_char_length = len(to_sent)
                        max_len = int(get_var(file_path, "max_length"))
                        if len(to_sent) > max_len:
                            for i in range(max_len, max_len+100):
                                if to_sent[i] == " " or to_sent[i] == "\n" or to_sent[i] == "\r":
                                    send_char_length = i
                                    break
                        if send_char_length < len(to_sent):
                            to_sent = to_sent[:send_char_length] + \
                                    "\n\nThis mail was sent to conference: **" + \
                                    new_mail.receiver_address + \
                                    "**s, you may read it in its entirety in your mail inbox."
                        print(to_sent)
                        await channel.send(to_sent)

    client.run(get_var(file_path, "bot_token"))

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

# Kinda itchy, but it works, so who am I to judge?
def parse_info(info):
    different_names = []
    res_name = ""
    res_address = ""
    for (name, encoding) in info:
        if isinstance(name, bytes):
            if encoding is None:
                name = name.decode("utf8")
            else:
                name = name.decode(encoding)
        different_names.append(name)

    if len(different_names) == 1:
        if "@" in different_names[0]:
            new_names = different_names[0].split("<")
            if len(new_names) == 1:
                res_name = new_names[0]
                res_address = new_names[0]
            else:
                res_name = new_names[0].strip()
                res_address = new_names[1].strip().replace(">", "").replace(" ", "")
        else:
            res_name = different_names[0]
    else:
        res_name = different_names[0]
        for diff_name in different_names[1:]:
            if "@" in diff_name:
                new_names = diff_name.split("<")
                if len(new_names) == 1:
                    to_use = new_names[0]
                else:
                    to_use = new_names[1]
                new_names = to_use.split(">")
                res_address = new_names[0]
                break

    if len(res_name) == 0:
        res_name = res_address
    return res_name, res_address



def handle_subject_and_sender(content):
    subject, subject_encoding = email.header.decode_header(content["Subject"])[0]
    if isinstance(subject, bytes):
        if subject_encoding is None:
            subject = subject.decode("utf-8")
        else:
            subject = subject.decode(subject_encoding)
    sender_name, sender_mail = parse_info(email.header.decode_header(content["From"]))
    receiver_name, receiver_mail = parse_info(email.header.decode_header(content["To"]))

    # receiver_address = email.header.decode_header(content["From"])[1][0].decode("utf-8").replace(" ", "").replace("<", "").replace(">", "")
    return subject, sender_name, sender_mail, receiver_mail


def handle_mail(id, imap_server):
    status, mail = imap_server.fetch(id, '(RFC822)')
    if status != 'OK':
        print("ERROR: Could not fetch mail with id: ", id, ". Response is: ", status)
        return
    mail_response = MailContent()
    for response_part in mail:
        # Dumb condition, because response may not fit in one bytestream so it is as array,
        # lets hope it won't make and complications. Maybe it has different reason.
        if isinstance(response_part, tuple):
            mail_content = email.message_from_bytes(response_part[1])
            # Get Subject and sender of mail
            subject, sender, sender_address, receiver_address = handle_subject_and_sender(mail_content)
            mail_response.sender = sender
            mail_response.subject = subject
            mail_response.sender_address = sender_address
            mail_response.receiver_address = receiver_address
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
        print("ERROR: Could not set mail with id: ", id, " as seen. Response is: ", status)




# Press the green button in the gutter to run the script.
if __name__ == '__main__':

    config_file = "config.json"
    # imap = login_to_imap_with_config(config_file)
    # unseen_messages = find_unseen_in_inbox(imap)
    # new_mails_to_print = []
    # for message_id in unseen_messages[0].split():
    #     mail = handle_mail(message_id, imap)
    #     set_mail_as_seen(imap, message_id)
    #     if (len(mail.message) != 0):
    #         new_mails_to_print.append(mail)
    discord_bot = initialize_bot(config_file)


