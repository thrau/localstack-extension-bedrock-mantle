#!/usr/bin/env bash
# Build, deploy, and invoke the Bedrock Mantle OpenAI Lambda example once.
set -euo pipefail

FUNCTION_NAME="${FUNCTION_NAME:-bedrock-mantle-openai-example}"
REGION="${AWS_DEFAULT_REGION:-us-east-1}"
RUNTIME="${RUNTIME:-python3.12}"
ROLE_ARN="${ROLE_ARN:-arn:aws:iam::000000000000:role/lambda-execution-role}"
EVENT="${EVENT:-{\"prompt\":\"Please respond with a snarky comment about Amazon Web Services.\",\"model\":\"smollm2:360m\"}}"

# The extension adds AWS_BEDROCK_BASE_URL to Docker Lambda containers. Do not
# override it here: the function deliberately verifies that the injection works.
command -v lstk >/dev/null || { echo "lstk is required (LocalStack CLI wrapper)." >&2; exit 1; }
command -v python3 >/dev/null || { echo "python3 is required." >&2; exit 1; }

workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT
mkdir -p "$workdir/package"

# Vendor the OpenAI client because standard Lambda Python runtimes do not include it.
python3 -m pip install --quiet --target "$workdir/package" -r requirements.txt
cp lambda_function.py "$workdir/package/"
(
  cd "$workdir/package"
  zip -qr "$workdir/function.zip" .
)

aws=(lstk aws --region "$REGION")
if "${aws[@]}" lambda get-function --function-name "$FUNCTION_NAME" >/dev/null 2>&1; then
  echo "Updating Lambda $FUNCTION_NAME ..."
  "${aws[@]}" lambda update-function-code \
    --function-name "$FUNCTION_NAME" --zip-file "fileb://$workdir/function.zip" >/dev/null
else
  echo "Creating Lambda $FUNCTION_NAME ..."
  "${aws[@]}" lambda create-function \
    --function-name "$FUNCTION_NAME" \
    --runtime "$RUNTIME" \
    --handler lambda_function.handler \
    --role "$ROLE_ARN" \
    --timeout 60 \
    --zip-file "fileb://$workdir/function.zip" >/dev/null
fi

# Creation can briefly leave a Lambda Pending. This is a bounded readiness check,
# not a retry of the model request: the Lambda is still invoked exactly once.
for attempt in $(seq 1 30); do
  # lstk can print setup advice before the AWS CLI's --output text value.
  state="$("${aws[@]}" lambda get-function-configuration \
    --function-name "$FUNCTION_NAME" --query State --output text | tail -n 1)"
  if [[ "$state" == "Active" ]]; then
    break
  fi
  if [[ "$state" == "Failed" ]]; then
    echo "Lambda entered the Failed state; not invoking it." >&2
    exit 1
  fi
  if [[ "$attempt" == "30" ]]; then
    echo "Lambda was still $state after 30 seconds; not invoking it." >&2
    exit 1
  fi
  sleep 1
done

# Intentionally invoke only once. A failure is reported for diagnosing the
# extension or environment instead of being hidden by unbounded retries.
payload_file="$workdir/response.json"
echo "Invoking Lambda once ..."
invoke_result="$("${aws[@]}" lambda invoke \
  --function-name "$FUNCTION_NAME" \
  --payload "$EVENT" \
  --log-type Tail \
  "$payload_file")"
printf '%s\n' "$invoke_result"

echo
printf '%s\n' 'Lambda payload:'
python3 -m json.tool "$payload_file" 2>/dev/null || cat "$payload_file"

if grep -q '"FunctionError"' <<<"$invoke_result"; then
  echo "Lambda returned FunctionError; no further invocations will be attempted." >&2
  exit 1
fi
