"""Lambda handler that calls Bedrock Mantle through OpenAI's Python SDK."""

import json
import os

from aws_lambda_powertools import Logger
from openai import OpenAI
from openai.providers import bedrock

logger = Logger("lambda-function-example")


@logger.inject_lambda_context(log_event=True)
def handler(event, context):
    """Generate a chat completion.

    Optional event fields:
      - prompt: user message (default: a short health-check question)
      - model: Ollama model name exposed by LocalStack Bedrock (default: smollm2:360m)
    """
    event = event or {}
    prompt = event.get("prompt", "Please respond with a snarky comment about Amazon Web Services.")
    model = event.get("model", "smollm2:360m")

    logger.info("environment", extra={"env": dict(os.environ)})

    # Bedrock Mantle implements OpenAI's /v1 API.  Its local endpoint does not
    # authenticate requests, but the OpenAI SDK requires an API key value.
    client = OpenAI(
        provider=bedrock(
            endpoint="mantle",
            api_key=None,  # Force IAM/SigV4 authentication
        )
    )

    try:
        response = client.responses.create(
            model=model,
            input=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        logger.exception("Error while invoking response")
        return {
            "statusCode": 500,
            "body": {
                "error": True,
                "message": f"{e}",
            },
        }

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "model": response.model,
                "text": response.output_text,
            }
        ),
    }
