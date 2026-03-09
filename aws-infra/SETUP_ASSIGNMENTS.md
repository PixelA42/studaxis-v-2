# Assignments API setup (teacher dashboard “Assign to Class”)

This lets the teacher dashboard create and list assignments (quizzes/notes per class) via API Gateway and the Assignment Manager Lambda.

## 1. Prerequisites

- **DynamoDB table** `studaxis-assignments` with partition key `assignment_id` (String).  
  If missing, create it or run:
  ```powershell
  cd aws-infra
  .\auto_provision_aws.ps1
  ```
- **AWS CLI** configured with credentials for the same account/region (`ap-south-1`).

## 2. Deploy the Assignment Manager Lambda

From `aws-infra`:

```powershell
.\deploy-lambdas.ps1
```

This will:

- Package `lambda/assignment_manager/` and deploy **studaxis-assignment-manager-dev**.
- Create the IAM role **studaxis-assignment-manager-role-dev** (with DynamoDB access to `studaxis-assignments`) if it does not exist.

## 3. Wire API Gateway to the Lambda

From `aws-infra`:

```powershell
.\setup-assignments-api.ps1
```

This will:

- Add **API Gateway invoke permission** for the Assignment Manager Lambda.
- Create **/assignments** and **/assignments/{id}** on API `yjyn9jsugc`.
- Set **POST** and **GET** on `/assignments`, **DELETE** on `/assignments/{id}`, and **OPTIONS** for CORS.
- Deploy the API to the **dev** stage.

## 4. Teacher dashboard

- `teacher-dashboard-web/.env` should have:
  ```bash
  VITE_API_GATEWAY_URL=https://yjyn9jsugc.execute-api.ap-south-1.amazonaws.com/dev
  ```
- Restart the dashboard (`npm run dev`). Then:
  - **Quiz Generator** → Generate a quiz → **Assign to Class** creates an assignment.
  - **Assignments** tab lists assignments for the selected class.

## Endpoints (after setup)

| Method | URL | Purpose |
|--------|-----|--------|
| POST | `.../dev/assignments` | Create assignment (body: `teacher_id`, `class_code`, `content_type`, `content_id`, `title`, etc.) |
| GET | `.../dev/assignments?class_code=XXX` | List assignments for a class |
| DELETE | `.../dev/assignments/{id}` | Delete assignment (body: `teacher_id`) |

## Troubleshooting

- **403 from API Gateway**  
  Run `.\setup-assignments-api.ps1` again so the Lambda has `apigateway-invoke-assignments` permission and the methods use **Authorization: NONE**.

- **Empty list / create fails**  
  Confirm the **dev** stage is deployed (script deploys to `dev`). Ensure `VITE_API_GATEWAY_URL` uses the same stage (e.g. `.../dev`).

- **DynamoDB errors in Lambda**  
  Ensure the table `studaxis-assignments` exists and the role `studaxis-assignment-manager-role-dev` has DynamoDB permissions for that table (handled by `deploy-lambdas.ps1` when it creates the role).
