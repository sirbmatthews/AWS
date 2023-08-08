#!/usr/bin/env python3
import os

import aws_cdk as cdk

from updatereplace_deletion_policies.updatereplace_deletion_policies_stack import UpdatereplaceDeletionPoliciesStack


app = cdk.App()
UpdatereplaceDeletionPoliciesStack(
    app, 
    "UpdatereplaceDeletionPoliciesStack",
    env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION'))
    )

app.synth()
