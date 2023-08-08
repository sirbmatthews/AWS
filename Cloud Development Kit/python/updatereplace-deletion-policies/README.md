# How to Set an UpdateReplacePolicy and a DeletePolicy on a Resource

### Adding an DeletePolicy and setting it to Delete
```
resource.apply_removal_policy(cdk.RemovalPolicy.DESTROY)
```

### Adding an UpdateReplacePolicy and setting it to Delete
```
resource.cfn_options.update_replace_policy = cdk.CfnDeletionPolicy.DELETE
```