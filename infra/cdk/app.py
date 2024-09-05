#!/usr/bin/env python3
import os

import aws_cdk as cdk

from codepipeline.lambda_deploy import CodePipelineStack


app = cdk.App()
CodePipelineStack(
    app,
    construct_id="CodePipelineLambdaDeployStack",
)

app.synth()