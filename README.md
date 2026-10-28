# Bedrock Mantle LocalStack Extension

Emulates [Bedrock Mantle](https://github.com/awslabs/bedrock-mantle) by exposing the
OpenAI-compatible API provided by Ollama through LocalStack endpoints. The extension
uses LocalStack Bedrock's `Ollama` backend, so Ollama is started and managed by
LocalStack.

## Install

To install the extension, add to your environment

```
EXTENSION_AUTO_INSTALL=git+https://github.com/thrau/localstack-extension-bedrock-mantle/#egg=localstack-extension-bedrock-mantle
```

or run

```sh
localstack extensions install "git+https://github.com/thrau/localstack-extension-bedrock-mantle/#egg=localstack-extension-bedrock-mantle"
```

## Usage

To connect to AWS bedrock mantle, your OpenAI code might look as simple as this.

```python
client = OpenAI(
    provider=bedrock(
        endpoint="mantle",
        api_key=None,  # Force IAM/SigV4 authentication
    )
)
```
The extension automatically configures your Lambda containers to connect to localstack.

## How it works

Requests to either of these endpoint forms are proxied directly to Ollama:

- `http://bedrock-mantle.<region>.localhost.localstack.cloud:4566/v1/...`
- `http://bedrock-mantle.<region>.api.aws/v1/...`

For example, use `https://bedrock-mantle.us-east-1.localhost.localstack.cloud/v1`
as an OpenAI base URL.

On load, the extension appends the following Docker flag to
`LAMBDA_DOCKER_FLAGS`, making the emulator available to Docker Lambda functions:

```text
-e AWS_BEDROCK_BASE_URL=http://bedrock-mantle.us-east-1.localhost.localstack.cloud:4566/v1
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
