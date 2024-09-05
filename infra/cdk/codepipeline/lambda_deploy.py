from aws_cdk import (
    Stack,
    RemovalPolicy,
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
        bucket = self._get_bucket_s3('artifacts-pipeline')
        source_action, source_output = self._get_source()
        environment_variables={
            "BUCKET_NAME": codebuild.BuildEnvironmentVariable(
                value=bucket.bucket_name
            )
        }
        test_action = self._get_codebuild_stage('Test', 'TEST', 1, source_output)
        build_action = self._get_codebuild_stage('Build', 'BUILD', 1, source_output, environment_variables)

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

    def _get_codebuild_stage(self, action_name, action_type, run_order, source_input, environment_variables={}):
        build_spec = codebuild.BuildSpec.from_source_filename(f"{self.buildspec_path}/{action_name.lower()}.yml")
        project = codebuild.PipelineProject(self, action_name.title(), build_spec=build_spec)
        build_action = codepipeline_actions.CodeBuildAction(
            action_name=action_name.title(),
            project=project,
            input=source_input,
            run_order=run_order,
            environment_variables=environment_variables,
            type=getattr(codepipeline_actions.CodeBuildActionType, action_type.upper())
        )

        return build_action

    def _get_bucket_s3(self, bucket_name):
        return s3.Bucket(
                    self,
                    bucket_name,
                    auto_delete_objects=True,
                    removal_policy=RemovalPolicy.DESTROY
                )
