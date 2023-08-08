from aws_cdk import (
    RemovalPolicy,
    CfnDeletionPolicy,
    Stack,
    aws_s3 as s3,
)
from constructs import Construct

class UpdatereplaceDeletionPoliciesStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

               # create an S3 bucket
        bucket = s3.Bucket(
            scope = self, 
            id = "UpdateReplacePolicyDeletionPolicyBucket"
        )

        resource = bucket.node.find_child("Resource")

        # Add deletion policy and set it to delete
        resource.apply_removal_policy(RemovalPolicy.DESTROY)
        
        # Add update replace policy and set it to delete
        resource.cfn_options.update_replace_policy = CfnDeletionPolicy.DELETE
