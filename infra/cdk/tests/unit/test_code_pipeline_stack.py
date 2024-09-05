import aws_cdk as core
import aws_cdk.assertions as assertions

from code_pipeline.code_pipeline_stack import CodePipelineStack

# example tests. To run these tests, uncomment this file along with the example
# resource in code_pipeline/code_pipeline_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = CodePipelineStack(app, "code-pipeline")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
