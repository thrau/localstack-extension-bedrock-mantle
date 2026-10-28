# Bedrock Mantle LocalStack Extension

Emulates [Bedrock Mantle](https://github.com/awslabs/bedrock-mantle) by exposing the
OpenAI-compatible API provided by Ollama through LocalStack endpoints. The extension
uses LocalStack Bedrock's `Ollama` backend, so Ollama is started and managed by
LocalStack.

Requests to either of these endpoint forms are proxied directly to Ollama:

- `https://bedrock-mantle.<region>.localhost.localstack.cloud/v1/...`
- `https://bedrock-mantle.<region>.api.aws/v1/...`

For example, use `https://bedrock-mantle.us-east-1.localhost.localstack.cloud/v1`
as an OpenAI base URL.

On load, the extension appends the following Docker flag to
`LAMBDA_DOCKER_FLAGS`, making the emulator available to Docker Lambda functions:

```text
-e AWS_BEDROCK_BASE_URL=bedrock-mantle.us-east-1.localhost.localstack.cloud
```

## Local development

Install development dependencies with `make install`. Run `make lint` to check lint
rules, import ordering, and formatting with Ruff, or `make format` to apply automatic
fixes and format the code.

Build the source distribution and wheel with `make dist` (using Hatch and the
Hatchling build backend). Artifacts are written to `dist/`.

```bash
localstack extensions dev enable .
EXTENSION_DEV_MODE=1 localstack start
```
