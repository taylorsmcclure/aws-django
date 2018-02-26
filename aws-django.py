#!/usr/bin/env python3
## Author: Taylor McClure
## Source: https://github.com/taylorsmcclure/aws-django


import os
import time
import boto3
import random
import string
import urllib
from urllib import request
import argparse



deploy_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
django_deployment_id = 'django-deployment-{}'.format(deploy_id)


def load_user_data():
    '''
    Loads userdata from djange_user_data.sh
    returns: data (str)
    '''
    with open('django_user_data.sh', 'r') as f:
        data = f.read()

    return data


def create_ec2_keypair():
    '''
    Before creating an EC2 instance this funciton creates a new keypair and
    saves the private key to .secrets/ dir with limited file permissions
    returns: pem_path (str)
    '''
    keypair = client.create_key_pair(KeyName=django_deployment_id)
    private_key = keypair['KeyMaterial']

    pem_path = '.secrets/private_key-{}.pem'.format(django_deployment_id)
    with open(pem_path, 'w') as f:
        f.writelines(private_key)
        f.close()

    os.chmod(pem_path, 0o400)

    return pem_path


def create_vpc():
    '''
    This function creates the VPC, subnet, IGW, and modifies the route table
    in preparation for launching the EC2 instance
    returns: vpc.id str, subnet.id str
    '''
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
    '''
    Function that actually creates the EC2 instance. In addition it will also
    create a security group, implement sg rules, allocate and assign an EIP,
    and will poll for the django app to be up.
    returns: return_message (str)
    '''
    # Create security group
    sg = client.create_security_group(
        Description=django_deployment_id,
        GroupName=django_deployment_id,
        VpcId=vpc_id,
    )
    sg_id = sg['GroupId']

    # Add rules
    # TODO: Limit SSH to only the /32 of the person executing this script
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

    # Load userdata to execute while launching
    django_user_data = load_user_data()

    # Create a new private/pub key on AWS then download it locally.
    pem_path = create_ec2_keypair()


    instance = ec2.create_instances(
        ImageId='ami-1b791862',
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.micro',
        SubnetId=subnet_id,
        KeyName=django_deployment_id,
        UserData=django_user_data,
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
        alloc_resp = client.allocate_address(Domain='vpc')
        assoc_resp = client.associate_address(AllocationId=alloc_resp['AllocationId'],
                                         InstanceId=instance_id)
    except Exception as e:
        print(e)

    pub_ip = alloc_resp['PublicIp']
    django_resp = None
    for i in range(15):
        try:
            django_resp = request.urlopen('http://{}'.format(pub_ip), timeout=1)
            if django_resp.getcode() != 200:
                continue
            else:
                print('Django app is up!')
                break
        except urllib.error.URLError as e:
            print('Django app not up yet, retrying...')
            time.sleep(10)
            continue

    if django_resp.getcode() != 200 or django_resp == None:
        print('Something went wrong with cloud-init script, django app is not up...')
        os.exit(1)

    return_message = '''
                Connect to {0} using the following string in your terminal\n\n
                ssh -i {1} ubuntu@{2}\n\n
                To see the Django app point your browser to: http://{2}/
                '''.format(instance_id, pem_path, pub_ip)

    return return_message


def _create_keypair():
    # TODO: Don't think I have time to implement
    # https://stackoverflow.com/a/9795584
    pass


def main(action):
    '''
    Main function that interacts with VPC and EC2 components of deployment.
    '''

    if action == 'run':
        # create_conns(access_key, secret_access_key, region)
        vpc_id, subnet_id = create_vpc()
        print(create_ec2(vpc_id, subnet_id))
    else:
        print('Not a supported action')
        os.exit(1)


parser = argparse.ArgumentParser(description='This script will provision an EC2 instance that will run the default installation of Django.')
parser.add_argument('action', choices=['run'],
                    help='Choose an action to either provision the instance or remove it.')
parser.add_argument('--access-key', default=None, help='AWS access key')
parser.add_argument('--secret-access-key', default=None, help='AWS secret access key')
# TODO: Add choices for all AWS regions
parser.add_argument('--region', default='eu-west-1', help='AWS region to launch instance')

args = parser.parse_args()

if args.access_key and args.secret_access_key is not None:
    client = boto3.client('ec2', region_name=args.region,
                            aws_access_key_id=args.access_key,
                            aws_secret_access_key=args.secret_access_key)

    ec2 = boto3.resource('ec2', region_name=args.region,
                            aws_access_key_id=args.access_key,
                            aws_secret_access_key=args.secret_access_key)
else:
    client = boto3.client('ec2')
    ec2 = boto3.resource('ec2')

main(args.action)
