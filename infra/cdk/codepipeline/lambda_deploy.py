from aws_cdk import (
    Stack,
    RemovalPolicy,
    CfnCapabilities,
    aws_codepipeline as codepipeline,
    aws_s3 as s3,
    aws_codebuild as codebuild,
    aws_codepipeline_actions as codepipeline_actions
)
from constructs import Construct
import boto3
import os

class CodePipelineStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.buildspec_path = "infra/cdk/codepipeline/buildspec"
        self.infra_lambda_path = "infra/cloudformation/lambda.yml"
        source_action, source_output = self._get_source()
        bucket = self._get_bucket_s3('artifacts-pipeline')

        test_action, _ = self._get_codebuild_action('Test', 'TEST', source_output)
        build_action, build_output = self._get_codebuild_action('Build', 'BUILD', source_output)
        infra_action = self._get_cloudformation_action('Deploy', 'LambdaDeploy', source_output, build_output)
        approval_action = self._get_approval_action(1)
        destroy_infra_action = self._get_delete_cloudformation_action('Destroy', 'LambdaDestroy', 2)

        pipeline = codepipeline.Pipeline(self, "pipeline-lambda-deploy",
            artifact_bucket=bucket,
            pipeline_name="pipeline-lambda-deploy",
            stages=[
                codepipeline.StageProps(
                    stage_name="Source",
                    actions=[source_action]
                ),
                codepipeline.StageProps(
                    stage_name="CI",
                    actions=[
                        build_action,
                        test_action
                    ]
                ),
                codepipeline.StageProps(
                    stage_name="CD",
                    actions=[infra_action]
                ),
                codepipeline.StageProps(
                    stage_name="Destroy",
                    actions=[
                        approval_action,
                        destroy_infra_action
                    ]
                )
            ]
        )

    def _get_source(self):
        connection_arn = self._get_connection_arn()
        source_output = codepipeline.Artifact()
        source_action = codepipeline_actions.CodeStarConnectionsSourceAction(
            action_name="Github_Source",
            output=source_output,
            branch=os.environ['GITHUB_BRANCH'],
            owner=os.environ['GITHUB_REPOSITORY_OWNER'],
            repo=os.environ['GITHUB_REPOSITORY_NAME'],
            connection_arn=connection_arn,
        )

        return source_action, source_output

    def _get_connection_arn(self, provider='GitHub'):
        client = boto3.client('codestar-connections')
        response = client.list_connections(ProviderTypeFilter=provider)

        for connection in response['Connections']:
            if connection['ConnectionStatus'] == 'AVAILABLE':
                return connection['ConnectionArn']
        else:
            raise Exception("No connection found")

    def _get_codebuild_action(self, action_name, action_type, source_input):
        build_spec = codebuild.BuildSpec.from_source_filename(f"{self.buildspec_path}/{action_name.lower()}.yml")
        project = codebuild.PipelineProject(self, action_name.title(), build_spec=build_spec)
        codebuild_output = codepipeline.Artifact()
        codebuild_action = codepipeline_actions.CodeBuildAction(
            action_name=action_name.title(),
            project=project,
            input=source_input,
            outputs=[codebuild_output],
            type=getattr(codepipeline_actions.CodeBuildActionType, action_type.upper())
        )

        return codebuild_action, codebuild_output

    def _get_bucket_s3(self, bucket_name):
        return s3.Bucket(
                    self,
                    bucket_name,
                    auto_delete_objects=True,
                    removal_policy=RemovalPolicy.DESTROY
                )

    def _get_cloudformation_action(self, action_name, stack_name, source_input, build_output):
        return codepipeline_actions.CloudFormationCreateUpdateStackAction(
            action_name=action_name,
            stack_name=stack_name,
            admin_permissions=True,
            cfn_capabilities=[CfnCapabilities.AUTO_EXPAND],
            template_path=source_input.at_path(self.infra_lambda_path),
            extra_inputs=[build_output],
            parameter_overrides={
                "S3BucketName": build_output.bucket_name,
                "S3Key": build_output.object_key
            },
        )

    def _get_delete_cloudformation_action(self, action_name, stack_name, run_order):
        return codepipeline_actions.CloudFormationDeleteStackAction(
            action_name=action_name,
            stack_name=stack_name,
            admin_permissions=True,
            run_order=run_order,
        )
    def _get_approval_action(self,run_order):
        return codepipeline_actions.ManualApprovalAction(
            action_name="ManualApproval",
            additional_information="Approve to deploy",
            run_order=run_order
        )