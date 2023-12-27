from aws_cdk import (
    Stack,
    Tags,
    aws_ec2 as ec2,
)
from constructs import Construct
import string, random

class VpcStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        #  Create VPC
        vpc = ec2.Vpc(
            self, 
            'VPC', 
            ip_addresses = ec2.IpAddresses.cidr('10.0.0.0/16'),
            enable_dns_hostnames = True,
            enable_dns_support = True,
            default_instance_tenancy = ec2.DefaultInstanceTenancy.DEFAULT,

            subnet_configuration = [ 
                ec2.SubnetConfiguration(
                    name = 'Public',
                    subnet_type = ec2.SubnetType.PUBLIC,
                    cidr_mask =19, 
                    map_public_ip_on_launch = True
                ),

                ec2.SubnetConfiguration(
                    name = 'Private',
                    subnet_type = ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask = 19
                )
            ],
            nat_gateways = 1,
        )
        
        # Add Tags to VPC
        Tags.of(vpc).add('Name', 'VPC')

        # Add Tags to Private Subnets
        subnet_list = vpc.select_subnets(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)
        for i, subnet in enumerate(subnet_list.subnets):
            Tags.of(subnet).add('Name', 'PrivateSubnet' + str(i + 1))
        
        # Add Tags to Public Subnets
        subnet_list = vpc.select_subnets(subnet_type=ec2.SubnetType.PUBLIC)
        for i, subnet in enumerate(subnet_list.subnets):
            Tags.of(subnet).add('Name', 'PublicSubnet' + str(i + 1))