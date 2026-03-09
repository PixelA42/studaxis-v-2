# Create New Class – AWS configuration

The teacher dashboard **Create New Class** feature creates a class in DynamoDB and shows a **new 6-character code every time**. It uses the Class Manager Lambda and API Gateway.

## What you need

1. **API Gateway**  
   - One REST API (e.g. `studaxis-teacher-api-dev`) with a stage (e.g. `prod`).  
   - Routes:
     - `POST /classes` → Class Manager Lambda  
     - `GET /classes?teacher_id=...` → Class Manager Lambda  
     - `GET /classes/verify?code=...` → Class Manager Lambda  
   - Deploy the API after adding routes.

2. **Lambda: Class Manager**  
   - Function name: e.g. `studaxis-class-manager-dev`  
   - Handler: `class_manager/handler.lambda_handler`  
   - Env: `CLASSES_TABLE_NAME=studaxis-classes`  
   - IAM: DynamoDB `PutItem`, `Scan` (and `Query` if using GSI) on `studaxis-classes`  
   - This Lambda generates a new 6-char code per class and writes to DynamoDB.

3. **DynamoDB**  
   - Table: `studaxis-classes`  
   - Attributes used: `class_id` (UUID), `teacher_id`, `class_name`, `class_code`, `created_at`  
   - Optional GSI: `teacher_id`–`created_at` for listing by teacher; `class_code` for verify.

4. **Teacher dashboard `.env`**  
   - Set **base** API Gateway URL (stage root, no path):
     - Correct: `VITE_API_GATEWAY_URL=https://your-api-id.execute-api.ap-south-1.amazonaws.com/prod`  
     - Wrong: `.../prod/generate-quiz` (Create Class calls `/classes`, not `/generate-quiz`).  
   - If you use one API for both quiz and classes, use the base URL; the app will call `/classes` and your other paths as needed.

## Quick checklist

- [ ] Class Manager Lambda deployed and wired to `studaxis-classes`  
- [ ] API Gateway has `POST /classes`, `GET /classes`, `GET /classes/verify` → Class Manager Lambda  
- [ ] API deployed to a stage (e.g. `prod`)  
- [ ] `VITE_API_GATEWAY_URL` = base URL of that stage (no trailing path)  
- [ ] Teacher can log in (teacher auth uses same or another backend)

After this, **Create New Class** in the dashboard will create a class and show a new code every time.

See `LAMBDA_DEPLOYMENT_GUIDE.md` for deployment steps and IAM.
