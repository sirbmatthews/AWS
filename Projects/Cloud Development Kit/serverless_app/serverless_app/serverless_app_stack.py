from aws_cdk import (
    CfnOutput, Fn, RemovalPolicy, Stack,
    aws_lambda as _lambda,
    aws_apigateway as apigateway,
    aws_ses as ses,
    aws_s3 as s3,
    aws_s3_deployment as s3_deployment,
    aws_iam as iam,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as sfn_tasks,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as cloudfront_origins
)
from constructs import Construct

class ServerlessAppStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create Lambda Role
        lambdaRole = iam.Role(
            self,
            'LambdaRole',
            assumed_by = iam.ServicePrincipal('lambda.amazonaws.com'),
            role_name = 'LambdaRuntimeRole',
            inline_policies = {
                'root': iam.PolicyDocument(
                    statements = [
                        iam.PolicyStatement(
                            actions = ['logs:CreateLogGroup', 'logs:CreateLogStream', 'logs:PutLogEvents'],
                            resources = ['arn:aws:logs:*:*:*'],
                            effect = iam.Effect.ALLOW
                        ),
                        iam.PolicyStatement(
                            actions = ['ses:*', 'states:*', 'sns:*'],
                            resources = ['*'],
                            effect = iam.Effect.ALLOW
                        )
                    ]
                )
            }


        )

        # Create Email Reminder Lambda function
        email = _lambda.Function(
            self,
            'email',
            function_name = 'email',
            handler = 'index.handler',
            runtime = _lambda.Runtime.PYTHON_3_12,
            role = lambdaRole,
            code = _lambda.Code.from_asset('src/email')
        )

        # Create SMS Reminder Lambda function
        sms = _lambda.Function(
            self,
            'sms',
            function_name = 'sms',
            handler = 'index.handler',
            runtime = _lambda.Runtime.PYTHON_3_12,
            role = lambdaRole,
            code = _lambda.Code.from_asset('src/sms')
        )

        # Create Step Function Role
        stepFunctionRole = iam.Role(
            self,
            'StepFunctionRole',
            assumed_by = iam.ServicePrincipal(Fn.join('.', ['states', self.region, 'amazonaws.com'])),
            role_name = 'RoleForStepFunction',
            inline_policies = {
                'root': iam.PolicyDocument(
                    statements = [
                        iam.PolicyStatement(
                            actions = ['lambda:InvokeFunction'],
                            resources = ['*'],
                            effect = iam.Effect.ALLOW
                        )
                    ]
                )
            }
        )

        # Step Function State Machine
        send_reminder = sfn.Wait( self, 'SendReminder', time = sfn.WaitTime.seconds_path('$.waitSeconds') )
        choice_state = sfn.Choice( self, 'ChoiceState')
        email_condition = sfn.Condition.string_equals('$.preference', 'email')
        sms_condition = sfn.Condition.string_equals('$.preference', 'sms')
        both_condition = sfn.Condition.string_equals('$.preference', 'both')
        email_task = sfn_tasks.LambdaInvoke( self,  'EmailReminder', state_name = 'EmailReminder', lambda_function = email )
        sms_task = sfn_tasks.LambdaInvoke (self, 'TextReminder', state_name = 'TextReminder', lambda_function = sms )
        both_task = sfn.Parallel( self, 'BothReminders', state_name = 'BothReminders' 
        ).branch( sfn_tasks.LambdaInvoke( self,  'EmailReminderPar', state_name = 'EmailReminderPar', lambda_function = email )
        ).branch( sfn_tasks.LambdaInvoke (self, 'TextReminderPar', state_name = 'TextReminderPar', lambda_function = sms ) )
        default_state = sfn.Fail( self, 'DefaultState', error = 'DefaultStateError', cause = 'No Matches!')
        next_state = sfn.Pass( self, 'NextState' )
        stepFunction = sfn.StateMachine( self,'StateMachine', state_machine_name = 'MyStateMachine', role = stepFunctionRole,
            definition = send_reminder.next(choice_state.when(email_condition, email_task).when(sms_condition, sms_task).when(both_condition, both_task).otherwise(default_state).afterwards().next(next_state))
        )
        stepFunction.node.default_child.override_logical_id('stepFunction')

        # Create API handler Lambda Function 
        api_handler = _lambda.Function(
            self,
            'api_handler',
            function_name = 'api_handler',
            handler = 'index.handler',
            runtime = _lambda.Runtime.PYTHON_3_12,
            role = lambdaRole,
            code = _lambda.Code.from_inline(
                Fn.join('"', 
                    [
                        'import boto3\nimport json\nimport os\nimport decimal\n\nSFN_ARN = ', 
                        Fn.get_att('stepFunction', 'Arn').to_string(),
                        '\n\nsfn = boto3.client("stepfunctions")\n\ndef lambda_handler(event, context):\n\tprint("EVENT:")\n\tprint(event)\n\tdata = json.loads(event["body"])\n\tdata["waitSeconds"] = int(data["waitSeconds"])\n\t\n\t# Validation Checks\n\tchecks = []\n\tchecks.append("waitSeconds" in data)\n\tchecks.append(type(data["waitSeconds"]) == int)\n\tchecks.append("preference" in data)\n\tchecks.append("message" in data)\n\tif data.get("preference") == "sms":\n\t\tchecks.append("phone" in data)\n\tif data.get("preference") == "email":\n\t\tchecks.append("email" in data)\n\n\t# Check for any errors in validation checks\n\tif False in checks:\n\t\tresponse = {\n\t\t\t"statusCode": 400,\n\t\t\t"headers": {"Access-Control-Allow-Origin":"*"},\n\t\t\t"body": json.dumps(\n\t\t\t\t{\n\t\t\t\t\t"Status": "Success", \n\t\t\t\t\t"Reason": "Input failed validation"\n\t\t\t\t},\n\t\t\t\tcls=DecimalEncoder\n\t\t\t)\n\t\t}\n\t# If none, run the state machine and return a 200 code saying this is fine :)\n\telse: \n\t\tsfn.start_execution(\n\t\t\tstateMachineArn=SFN_ARN,\n\t\t\tinput=json.dumps(data, cls=DecimalEncoder)\n\t\t)\n\t\tresponse = {\n\t\t\t"statusCode": 200,\n\t\t\t"headers": {"Access-Control-Allow-Origin":"*"},\n\t\t\t"body": json.dumps(\n\t\t\t\t{"Status": "Success"},\n\t\t\t\tcls=DecimalEncoder\n\t\t\t)\n\t\t}\n\treturn response\n\n# This is a workaround for: http://bugs.python.org/issue16535\nclass DecimalEncoder(json.JSONEncoder):\n\tdef default(self, obj):\n\t\tif isinstance(obj, decimal.Decimal):\n\t\t\treturn int(obj)\n\t\treturn super(DecimalEncoder, self).default(obj)\n\n'
                    ]
                )
            )
        )

        # Create Rest API
        api_reminder = apigateway.RestApi(
            self,
            'reminders',
            rest_api_name = 'reminders'
        )
        api_reminder.node.default_child.override_logical_id('apiReminders')

        # Create API Lambda Intergration
        api_reminder_integration = apigateway.LambdaIntegration(api_handler)

        # Create API Resource
        api_resource = api_reminder.root.add_resource('reminders')

        # Create API Resouce Method
        api_resource.add_method('POST', api_reminder_integration)

        # CfnOutput(self, "Reminder", value = Fn.get_att('reminder', ))

        # Create an S3 bucket
        website_bucket = s3.Bucket( 
            self, 
            'WebsiteBucket', 
            bucket_name = Fn.join('-', ['serverless-reminder-api', self.account]), 
            access_control = s3.BucketAccessControl.PRIVATE,
            # block_public_access = s3.BlockPublicAccess(
            #     block_public_policy = False,
            #     block_public_acls = False,
            #     ignore_public_acls = False,
            #     restrict_public_buckets = False
            # ),
            # website_index_document = 'index.html', 
            # website_error_document = 'error.html' 
            removal_policy = RemovalPolicy.DESTROY, 
        )

        # website_bucket.add_to_resource_policy(
        #     iam.PolicyStatement(
        #         actions = ['s3:GetObject'],
        #         effect = iam.Effect.ALLOW,
        #         resources = [ Fn.join('/', [website_bucket.bucket_arn, '*'])],
        #         principals = [ iam.AnyPrincipal() ]
        #     )
        # )

        deployment = s3_deployment.BucketDeployment(
            self,
            'S3 Deployment',
            destination_bucket = website_bucket,
            sources = [ s3_deployment.Source.asset('src/static_website')],
        )

        website_access_identity = cloudfront.OriginAccessIdentity(self, 'OriginAccessIdentity')
        website_bucket.grant_read(website_access_identity)

        website_distribution = cloudfront.Distribution(
            self,
            'WebsiteDistribution',
            default_root_object = 'index.html',
            default_behavior = cloudfront.BehaviorOptions(
                origin = cloudfront_origins.S3Origin(website_bucket, origin_access_identity = website_access_identity)
            )
        )

