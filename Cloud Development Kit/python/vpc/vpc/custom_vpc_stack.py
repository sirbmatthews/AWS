from aws_cdk import (
    Stack,
    CfnTag,
    Fn,
    aws_ec2 as ec2,
)
from constructs import Construct

class CustomVpcStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        #  Create VPC
        vpc = ec2.CfnVPC(
            self,
            "VPC",
            cidr_block = '10.0.0.0/16',
            enable_dns_hostnames = True,
            enable_dns_support = True,
            instance_tenancy = 'default',
            tags = [CfnTag(key = 'Name', value = 'VPC')]
        )
        
        # Subnets variables
        public_subnet_cidr = ['10.0.0.0/19', '10.0.32.0/19', '10.0.64.0/19']
        private_subnet_cidr = ['10.0.96.0/19', '10.0.128.0/19', '10.0.160.0/19']
        public_subnets = []
        private_subnets = []

        # Create Public Subnets
        for i, cidr in enumerate(public_subnet_cidr):
            public_subnets.append(
                ec2.CfnSubnet(
                    self,
                    "PublicSubnet" + str(i+1),
                    availability_zone = Fn.select(i, Fn.get_azs()),
                    cidr_block = cidr,
                    vpc_id = vpc.attr_vpc_id,
                    map_public_ip_on_launch = True,
                    tags = [CfnTag(key = 'Name', value = 'PublicSubnet' + str(i+1))]
                )
            )

        # Create Private Subnets
        for i, cidr in enumerate(private_subnet_cidr):
            private_subnets.append(
                ec2.CfnSubnet(
                    self,
                    "PrivateSubnet" + str(i+1),
                    availability_zone = Fn.select(i, Fn.get_azs()),
                    cidr_block = cidr,
                    vpc_id = vpc.attr_vpc_id,
                    map_public_ip_on_launch = True,
                    tags = [CfnTag(key = 'Name', value = 'PrivateSubnet' + str(i+1))]
                )
            )

        # Create Public Route Table
        public_route_table = ec2.CfnRouteTable(
            self,
            'PublicRouteTable',
            vpc_id = vpc.attr_vpc_id,
            tags = [CfnTag(key = 'Name', value = 'RouteTable')]
        )

         # Create Private Route Table
        private_route_table = ec2.CfnRouteTable(
            self,
            'PrivateRouteTable',
            vpc_id = vpc.attr_vpc_id,
            tags = [CfnTag(key = 'Name', value = 'RouteTable')]
        )

        # Create Public Subnet Route Table Associations
        for i, subnet in enumerate(public_subnets):
            ec2.CfnSubnetRouteTableAssociation(
                self,
                'PublicSubnetRouteTableAssociation' + str(i+1),
                route_table_id = public_route_table.attr_route_table_id,
                subnet_id = subnet.attr_subnet_id
            )
        # Create Private Subnet Route Table Associations
        for i, subnet in enumerate(private_subnets):
            ec2.CfnSubnetRouteTableAssociation(
                self,
                'PrivateSubnetRouteTableAssociation' + str(i+1),
                route_table_id = private_route_table.attr_route_table_id,
                subnet_id = subnet.attr_subnet_id
            )

        # Create Internet Gateway 
        internet_gateway = ec2.CfnInternetGateway(
            self,
            'InternetGateway',
            tags = [CfnTag(key = 'Name', value = 'InternetGateway')]
        )
        
        # Create Route for Internet Gateway
        routeIGW = ec2.CfnRoute(
            self,
            'RouteIGW',
            route_table_id = public_route_table.attr_route_table_id,
            destination_cidr_block = '0.0.0.0/0',
            gateway_id = internet_gateway.attr_internet_gateway_id
        )


        # Create VPC Internet Gateway Attachment
        vpc_gateway_attachment = ec2.CfnVPCGatewayAttachment(
            self,
            'VPCInternetGatewayAttachment',
            internet_gateway_id = internet_gateway.attr_internet_gateway_id,
            vpc_id = vpc.attr_vpc_id
        )

        # Create EIP
        eip = ec2.CfnEIP(
            self,
            'ElasticIP',
            domain = 'vpc',
            tags = [CfnTag(key = 'Name', value = 'ElasticIP')]
        )

        # Create NAT Gateway
        nat_gateway = ec2.CfnNatGateway(
            self, 
            'NATGateway',
            subnet_id = public_subnets[0].attr_subnet_id,
            allocation_id = eip.attr_allocation_id,
            tags = [CfnTag(key = 'Name', value = 'NATGateway')]
        )

        # Create Route for NAT Gateway
        routeNat = ec2.CfnRoute(
            self,
            'RouteNAT',
            route_table_id = private_route_table.attr_route_table_id,
            destination_cidr_block = '0.0.0.0/0',
            nat_gateway_id = nat_gateway.attr_nat_gateway_id
        )