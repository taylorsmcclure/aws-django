#!/usr/bin/env python3
## Author: Taylor McClure
## Source: https://github.com/taylorsmcclure/aws-django


import os
import time
import boto3
import random
import string
import argparse
# import OpenSSL


client = boto3.client('ec2')
ec2 = boto3.resource('ec2')
deploy_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
django_deployment_id = 'django-deployment-{}'.format(deploy_id)


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

    return vpc.id, subnet.id

def create_ec2(vpc_id, subnet_id):

    # Create security group
    sg = client.create_security_group(
        Description=django_deployment_id,
        GroupName=django_deployment_id,
        VpcId=vpc_id,
    )
    sg_id = sg['GroupId']

    # Add rules
    response = client.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=[
            {'IpProtocol': 'tcp',
             'FromPort': 80,
             'ToPort': 80,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': 'tcp',
             'FromPort': 22,
             'ToPort': 22,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
        ])

    instance = ec2.create_instances(
        ImageId='ami-1b791862',
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.micro',
        SubnetId=subnet_id,
        SecurityGroupIds=[
        sg_id
        ],
        TagSpecifications=[
        {
            'ResourceType': 'instance',
            'Tags': [
                {
                    'Key': 'Name',
                    'Value': django_deployment_id
                },
            ]
        },
        {
            'ResourceType': 'volume',
            'Tags': [
                {
                    'Key': 'Name',
                    'Value': django_deployment_id
                },
            ]
        }
        ])

    django_instance = instance[0]
    instance_id = instance[0].id

    # Allocate and associate EIP with instance
    instance[0].wait_until_running();
    try:
        allocation = client.allocate_address(Domain='vpc')
        response = client.associate_address(AllocationId=allocation['AllocationId'],
                                         InstanceId=instance_id)
    except Exception as e:
        print(e)


def _create_keypair():
    pass


def main(action, access_key, secret_access_key, region):

    if action == 'run':
        vpc_id, subnet_id = create_vpc()
        create_ec2(vpc_id, subnet_id)
    else:
        print('Not a supported action')
        os.exit(1)


parser = argparse.ArgumentParser(description='This script will provision an EC2 instance that will run the default installation of Django.')
parser.add_argument('action', choices=['run', 'delete'],
                    help='Choose an action to either provision the instance or remove it.')
parser.add_argument('--access-key', default=None, help='AWS access key')
parser.add_argument('--secret-access-key', default=None, help='AWS secret access key')
# TODO: Add choices for all AWS regions
parser.add_argument('--region', default='eu-west-1', help='AWS region to launch instance')

args = parser.parse_args()

main(args.action, args.access_key, args.secret_access_key, args.region)
