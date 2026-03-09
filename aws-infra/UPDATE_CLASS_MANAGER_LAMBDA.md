# Update class_manager Lambda via AWS CLI

Use this when you only changed `lambda/class_manager/` and want to update the deployed function without running the full deploy script.

## Prerequisites

- AWS CLI installed and configured (`aws configure`)
- Region: `ap-south-1` (or set `AWS_DEFAULT_REGION`)

## Option 1: One-liner (Git Bash / WSL)

From repo root:

```bash
cd aws-infra/lambda && rm -f class_manager.zip && cd class_manager && zip -r ../class_manager.zip . && cd .. && aws lambda update-function-code --function-name studaxis-class-manager-dev --zip-file fileb://class_manager.zip --region ap-south-1
```

## Option 2: PowerShell (Windows)

From repo root:

```powershell
cd aws-infra\lambda
if (Test-Path class_manager.zip) { Remove-Item class_manager.zip -Force }
Compress-Archive -Path "class_manager\*" -DestinationPath "class_manager.zip" -Force
aws lambda update-function-code --function-name studaxis-class-manager-dev --zip-file fileb://class_manager.zip --region ap-south-1
```

## Option 3: Step by step (any shell)

1. Go to the lambda folder:
   ```bash
   cd aws-infra/lambda
   ```

2. Create the zip (contents of `class_manager/`, not the folder itself):
   - **Bash:** `cd class_manager && zip -r ../class_manager.zip . && cd ..`
   - **PowerShell:** `Compress-Archive -Path "class_manager\*" -DestinationPath "class_manager.zip" -Force`

3. Update the function:
   ```bash
   aws lambda update-function-code --function-name studaxis-class-manager-dev --zip-file fileb://class_manager.zip --region ap-south-1
   ```

## Option 4: Full deploy script (all Lambdas)

To deploy/update all Lambdas (teacher_auth, class_manager, teacher_generate_notes):

- **Bash:** `cd aws-infra && ./deploy-lambdas.sh`
- **PowerShell:** `cd aws-infra; .\deploy-lambdas.ps1`

## Verify

After update, check that the function was updated:

```bash
aws lambda get-function --function-name studaxis-class-manager-dev --region ap-south-1 --query "Configuration.LastModified"
```

Or invoke a test (CORS preflight):

```bash
aws lambda invoke --function-name studaxis-class-manager-dev --region ap-south-1 --payload '{"httpMethod":"OPTIONS","path":"/classes"}' --cli-binary-format raw-in-base64-out out.json && type out.json
```

(PowerShell: use `Get-Content out.json` instead of `type out.json`.)
