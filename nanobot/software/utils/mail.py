"""
.. module:: mail
    :platform: Unix
    :synopsis: Module for sending emails

.. moduleauthor:: Graham Keenan <https://github.com/ShinRa26>

"""

import smtplib
from email.mime.multipart import MIMEMultipart 
from email.mime.text import MIMEText

SERVER = "smtp-mail.outlook.com"
PORT = 587

USERNAME = "ENTER EMAIL HERE"
PASSWD = "ENTER PASSWD HERE"


def send_email(platform_name: str, toaddr: str, body: str, flag=0):
    """Sends an email to a recipient

    Arguments:
        platform_name {str} -- Name of the platform
        toaddr {str} -- Recipient
        body {str} -- Message to send

    Keyword Arguments:
        flag {int} -- Flag for type of message (default: {0})
    """

    msg = MIMEMultipart()
    msg['From'] = USERNAME
    msg['To'] = toaddr

    if flag == 0:
        msg['Subject'] = "{} Update".format(platform_name)
    elif flag == 1:
        msg["Subject"] = "CRASH -- {} Error".format(platform_name)
    elif flag == 2:
        msg["Subject"] = "{} -- Generation Complete".format(platform_name)

    msg.attach(MIMEText(body, 'plain'))

    server = smtplib.SMTP(SERVER, PORT)
    server.starttls()
    server.login(USERNAME, PASSWD)
    text = msg.as_string()
    server.sendmail(USERNAME, toaddr, text)
    server.quit()


def notify(platform_name: str, emails: list, msg: str, flag=0):
    """Sends an email to all concerned parties

    Arguments:
        platform_name {str} -- Name of the platform
        emails {list} -- List of email addresses
        msg {str} -- Message to send

    Keyword Arguments:
        flag {int} -- Flag for the type of message (default: {0})
    """

    try:
        for addr in emails:
            send_email(platform_name, addr, msg, flag=flag)
    except Exception as e:
        if "Spam" in e.__str__():
            print("Apparently we're spamming...")
        else:
            print(e)
