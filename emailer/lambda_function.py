"""
This is a proof of concept to demonstrate how Alexa might be used to support the bids team.
"""

from __future__ import print_function
import boto3
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
import json
import hashlib
import jsonpickle


def verifyEmail(email):
    client = boto3.client('ses')
    response = client.list_verified_email_addresses()
    if email in response['VerifiedEmailAddresses']:
        return None
    else:
        response = client.verify_email_address(
            EmailAddress=email,
        )
        return True


def sendEmail(**kwargs):
    client = boto3.client('ses')
    msg = {}
    if kwargs is not None:
        for key, value in kwargs.items():
            msg[key] = value
            if 'To' not in kwargs:
                print("No 'To' provided, failing safely")
                raise SystemExit
            if 'From' not in kwargs:
                print("No 'From' provided, failing safely")
                raise SystemExit
            if 'Subject' not in kwargs:
                msg['Subject'] = 'DEFAULT SUBJECT: REPLACE ME'
            if 'Body' not in kwargs:
                print("No Body provided, failing safely")
                raise SystemExit

    if verifyEmail(msg['To']) is None:
        result = client.send_raw_email(RawMessage={
            'Data': msg['Body'].as_string()
            },
            Source=msg['From'],
            Destinations=[
                msg['To']
                ])
        print(result)
        return "I'm emailing you a mail with subject: %s" % msg['Subject']
    else:
        return 'Please go to your mail and verify your email address so we can send you an email'


def get_user_info(access_token):
    amazonProfileURL = 'https://api.amazon.com/user/profile?access_token='
    r = requests.get(url=amazonProfileURL+access_token)
    if r.status_code == 200:
        return r.json()
    else:
        return False

# --------------- Main handler ------------------


def lambda_handler(event, context):
    print(event)
    message_event = json.loads(event['Records'][0]['Sns']['Message'])
    print(message_event)
    # Now return the message to a format which MIMEEmail expects
    Body = jsonpickle.decode(message_event['Body'])
    emailProfile = message_event['To']
    resultResponse = sendEmail(To=emailProfile, Subject=message_event['Subject'], Body=Body)
