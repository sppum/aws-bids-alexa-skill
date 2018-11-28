"""
This is a proof of concept to demonstrate how Alexa might be used to support the bids team.
"""

#from __future__ import print_function
import parseTable
from bs4 import BeautifulSoup
import requests
import boto3
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import hashlib
from os import environ

EmailSnsTopic = environ.get('SNS_EMAIL_TOPIC')

response = requests.get('https://aws.amazon.com/tax-help/european-union/').text
boardUrl = requests.get('https://www.sec.gov/Archives/edgar/data/1018724/000119312510164087/dex991.htm').text

DUNS = '88-474-5530'
TAXID = '91-1646860'

#taxPdf = requests.get('https://inside.amazon.com/en/services/legal/us/spendingandtransaction/Documents/vendor.pdf').text


def push_sns(event, snsTopic):
    if os.getenv('AWS_SAM_LOCAL'):
        print('SAM_LOCAL DETECTED')
        sns = boto3.client('sns',
                           endpoint_url='http://localstack:4575',
                           region_name='us-east-1')
    else:
        sns = boto3.client('sns')
    response = sns.publish(
        TopicArn=snsTopic,
        Message=json.dumps(event)
    )
    return response
    

def getEO():
    """
    Parses an HTML table, returns a panda Dataframe
    """
    hp = parseTable.HTMLTableParser()
    soup = BeautifulSoup(boardUrl, 'html.parser')
    table = soup.find_all('table')
    board_table = hp.parse_html_table(table[3])
    boardTable = board_table.set_index([0])
    return boardTable


def getDirectors():
    """
    Parses an HTML table, returns a panda Dataframe
    """
    hp = parseTable.HTMLTableParser()
    soup = BeautifulSoup(boardUrl, 'html.parser')
    table = soup.find_all('table')
    board_table = hp.parse_html_table(table[0])
    boardTable = board_table.set_index([0])
    return boardTable


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


def getUrlDigest(url):
    m = hashlib.md5()
    m.update(url.content)
    digest = m.hexdigest()
    return digest


def sendTaxEmail(emailAddress, taxItem, description):
    client = boto3.client('ses')
    if verifyEmail(emailAddress) is None:
        msg = MIMEMultipart()
        msg['Subject'] = 'Here is the Amazon ' + description
        msg['From'] = emailAddress
        msg['To'] = emailAddress

        part = MIMEText('The Amazon %s is: %s' %
                        description, taxItem)
        msg.attach(part)

        result = client.send_raw_email(RawMessage={
            'Data': msg.as_string()
            },
            Source=msg['From'])
        print(result)
        return 'I am emailing you the tax item ' + description
    else:
        return 'Please go to your mail and verify your email address so we can email you the service description'


def get_user_info(access_token):
    amazonProfileURL = 'https://api.amazon.com/user/profile?access_token='
    r = requests.get(url=amazonProfileURL+access_token)
    if r.status_code == 200:
        return r.json()
    else:
        return False

# --------------- Main handler ------------------


def lambda_handler(event, context):
    print("Received event: ")
    print(event)
    alexa_event = json.loads(event['Records'][0]['Sns']['Message'])
    print("Alexa event: " + alexa_event)
    intent = alexa_event['request']['intent']
    if 'emailDirectors' in intent['name']:
        directors = getDirectors()
        directors = directors.to_dict()[2]
        return directors
    elif 'emailExecutives' in intent['name']:
        executives = getEO()
        executives = executives.to_dict()[2]
        return executives
    elif 'emailDUNS' in intent['name']:
        description = 'DUNS'
        response = push_sns(event, EmailSnsTopic)
        print("Pushed to topic: %s" % EmailSnsTopic)
        print(response)
        return response
    elif 'emailTAXID' in intent['name']:
        description = 'TAX ID'
        response = push_sns(event, EmailSnsTopic)
        print("Pushed to topic: %s" % EmailSnsTopic)
        print(response)
        return response
