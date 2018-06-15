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

response = requests.get('https://aws.amazon.com/tax-help/european-union/').text


def getTaxList():
    hp = parseTable.HTMLTableParser()
    soup = BeautifulSoup(response, 'html.parser')
    table = soup.find_all('table')
    tax_table = hp.parse_html_table(table[0])
    df = tax_table.set_index([0])
    return df


def getServiceDescription(serviceUrl):
    response = requests.get(serviceUrl).text
    soup = BeautifulSoup(response, 'html.parser')
    return soup.find('div', {'id': 'aws-page-content'})


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


def sendEmail(emailAddress, taxCountry, taxRate):
    client = boto3.client('ses')
    if verifyEmail(emailAddress) is None:
        msg = MIMEMultipart()
        msg['Subject'] = 'Here is the VAT rate for ' + taxCountry
        msg['From'] = emailAddress
        msg['To'] = emailAddress

        part = MIMEText('VAT Rate for %s: %s' %
                        (taxCountry, taxRate))
        msg.attach(part)

        result = client.send_raw_email(RawMessage={
            'Data': msg.as_string()
            },
            Source=msg['From'])
        print(result)
        return 'I am emailing you the VAT rate for ' + taxCountry
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


#taxRates = {'UK': '20%', 'Germany': '19%', 'France': '20%'}


def lambda_handler(event, context):
    print(event)
    alexa_event = json.loads(event['Records'][0]['Sns']['Message'])
    print(alexa_event)
    #intent = alexa_event['request']['intent']
    slot = alexa_event['request']['intent']['slots']
    tax_dict = getTaxList().to_dict()[1]
    if 'country' in slot.keys():
        taxCountry = slot['country']['value']
        print('We have the country: %s' % taxCountry)
        print('VAT Rate for %s = %s' % (taxCountry, tax_dict[taxCountry]))
    emailProfile = 'cmking@gmail.com'
    resultResponse = sendEmail(emailProfile, taxCountry, tax_dict[taxCountry])
    return (taxCountry, tax_dict[taxCountry])
