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
    emailAddress = ''
    subjectLine = ''
    msg = {}
    if kwargs is not None:
        for key, value in kwargs.items():
            msg[key] = value
            if emailAddress not in kwargs:
                print("No emailAddress provided, failing safely")
                raise SystemExit
            if subjectLine not in kwargs:
                subjectLine = 'DEFAULT SUBJECT: REPLACE ME'
                msg['subjectLine'] = subjectLine
            if body not in kwargs:
                print("No body provided, failing safely")
                raise SystemExit

    if verifyEmail(emailAddress) is None:
        msg = MIMEMultipart()
        msg['Subject'] = subjectLine
        msg['From'] = emailAddress
        msg['To'] = emailAddress

        msg.preamble = 'Multipart message.\n'

        part = MIMEText(msg['body'])
        msg.attach(part)

        #part = MIMEApplication(open('/tmp/service_description.pdf',
        #                            'rb').read())
        #part.add_header('Content-Disposition', 'attachment',
        #                filename='service_description.pdf')
        #msg.attach(part)

        result = client.send_raw_email(RawMessage={
            'Data': msg.as_string()
            },
            Source=msg['From'])
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
    body = jsonpickle.decode(message_event['body'])
    emailProfile = message_event['recipient']

    print("Email destination: %s" % emailProfile)
    print("Email subject: %s" % message_event['subjectLine'])
#    resultResponse = sendEmail(emailAddress=emailProfile, subjectLine=message_event['subjectLine'], body=body)
