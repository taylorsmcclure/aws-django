#!/usr/bin/env python3
## Author: Taylor McClure
## Source: https://github.com/taylorsmcclure/aws-django


import os
import boto3
import random
import string
import argparse


client = boto3.client('ec2')
ec2 = boto3.resource('ec2')
# vpc = boto3.resource('vpc')
deploy_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


def create_vpc():
    vpc = ec2.create_vpc(CidrBlock='10.1.0.0/16')
    subnet = vpc.create_subnet(CidrBlock='10.1.0.0/16')
    gateway = ec2.create_internet_gateway()
    vpc.attach_internet_gateway(InternetGatewayId=gateway.id)

    route_tables = client.describe_route_tables(
        Filters=[{'Name': 'vpc-id', 'Values': [vpc.id]}]
        )

    rtb_id = route_tables['RouteTables'][0]['RouteTableId']

    igw_route = client.create_route(
        RouteTableId=rtb_id,
        DestinationCidrBlock='0.0.0.0/0',
        GatewayId=gateway.id,
    )

    return vpc.id

def create_ec2():
    pass


def _create_keypair():
    pass


def main(action, access_key, secret_access_key, region):

    print(create_vpc())
    '''
    if action == 'run':
        create_vpc()

        instance = ec2.create_instances(
            ImageId='ami-1b791862',
            MinCount=1,
            MaxCount=1,
            InstanceType='t2.micro')
        print(instance[0].id)
    else:
        print('Not a supported action.')
        os.exit(1)
    '''


parser = argparse.ArgumentParser(description='This script will provision an EC2 instance that will run the default installation of Django.')
parser.add_argument('action', choices=['run', 'delete'],
                    help='Choose an action to either provision the instance or remove it.')
parser.add_argument('--access-key', default=None, help='AWS access key')
parser.add_argument('--secret-access-key', default=None, help='AWS secret access key')
# TODO: Add choices for all AWS regions
parser.add_argument('--region', default='eu-west-1', help='AWS region to launch instance')

args = parser.parse_args()

main(args.action, args.access_key, args.secret_access_key, args.region)
