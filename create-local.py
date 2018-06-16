#!/usr/bin/env python3
import localstack_client.session
from os import environ

# localstack is a bit odd
environ['AWS_ACCESS_KEY_ID']='foobar'
environ['AWS_SECRET_ACCESS_KEY']='foobar'
environ['AWS_DEFAULT_REGION']='foobar'

# Resources to create
resources = {'SNS_EMAIL_TOPIC': 'awsBidsAlexaSns-local',
             'SNS_COMPLIANCE_TOPIC': 'awsBidsComplianceSns-local',
             'SNS_TAX_TOPIC': 'awsBidsTaxSns-local',
             'SNS_DIRECTORS_TOPIC': 'awsBidsDirectorsSns-local',
             'DYNAMODB_TABLE': 'localstack-bids-table'}

# Clients
session = localstack_client.session.Session()
sns = session.client('sns')
ddb = session.client('dynamodb',
                     region_name='local',
                     endpoint_url='http://localhost:4569')

# Create resources
for k, v in resources.items():
    if 'TOPIC' in k:
        topic = sns.create_topic(
                Name=v
                )
        print('Created topic: %s' % topic)
    elif 'TABLE' in k:
        try:
            table = ddb.create_table(
                    AttributeDefinitions=[
                        {
                            'AttributeName': 'ServiceName',
                            'AttributeType': 'S'
                        },
                    ],
                    TableName=v,
                    KeySchema=[
                        {
                            'AttributeName': 'ServiceName',
                            'KeyType': 'HASH'
                        },
                    ],
                    ProvisionedThroughput={
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                        }
                    )
            print('Created table: %s' % table)
        except Exception as err:
            print('Table already exists: %s' % err)
    else:
        print('Unknown resource type: %s' % k)
        print('Consider adding a new client.')
