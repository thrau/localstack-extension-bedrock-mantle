# Bedrock Mantle OpenAI Lambda example

This example packages a Python Lambda that uses the official `openai` SDK against
Bedrock Mantle's OpenAI-compatible endpoint. It relies on the extension's
`AWS_BEDROCK_BASE_URL` Docker-Lambda injection, rather than hard-coding a host.

## Run

Start LocalStack with the Bedrock Mantle extension enabled, then run:

```bash
chmod +x deploy_and_invoke.sh
./deploy_and_invoke.sh
```

The script vendors `openai`, creates (or updates) a `python3.12` Lambda through
`lstk aws ...`, and invokes it exactly once. It prints the Lambda invocation
metadata and response payload. A function error or connection failure is left
visible for investigation; the script deliberately does not retry invocations.

The default model is `smollm2:360m`. Override the request, including the model name,
when your LocalStack Bedrock/Ollama setup exposes another model:

```bash
./deploy_and_invoke.sh
```

Other supported environment overrides are `FUNCTION_NAME`, `AWS_DEFAULT_REGION`,
`RUNTIME`, and `ROLE_ARN`.
