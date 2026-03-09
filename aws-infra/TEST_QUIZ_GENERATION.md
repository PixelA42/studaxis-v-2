# Test Quiz Generation on AWS Teacher Dashboard

Quick steps to test quiz generation from the teacher dashboard against API Gateway + Lambda (Bedrock).

## Prerequisites

1. **API Gateway** `yjyn9jsugc` (studaxis-teacher-api-dev) has:
   - Resource: `POST /generateQuiz`
   - Integration: Lambda `studaxis-quiz-generation-dev`, **Lambda Proxy Integration**
   - **Authorization: NONE** (so the browser can call it without AWS SigV4). If you see 403, set the method auth to NONE in the console.
   - CORS: OPTIONS method returning `Access-Control-Allow-Origin: *` (or your dashboard origin).

2. **Lambda** `studaxis-quiz-generation-dev` is deployed and has:
   - Bedrock permissions (`bedrock:InvokeModel`)
   - Env: `BEDROCK_REGION=ap-south-1`, `BEDROCK_MODEL_ID=...` (or defaults)

3. **Teacher dashboard** `.env`:
   ```bash
   VITE_API_GATEWAY_URL=https://yjyn9jsugc.execute-api.ap-south-1.amazonaws.com/dev
   ```
   Use the **actual stage name** (this API has `dev` and `Stage`, not `prod`). No path suffix; the app calls `/generateQuiz`.

## Test from the dashboard

1. **Start the teacher dashboard** (from repo root):
   ```powershell
   cd aws-infra\teacher-dashboard-web
   npm run dev
   ```

2. **Log in** (use your class code / teacher auth).

3. Open **Quiz Generator** from the sidebar.

4. Fill the form:
   - **Topic** (e.g. "Newton's Laws")
   - **Subject** (e.g. Physics)
   - **Number of questions** (e.g. 5)
   - **Difficulty** (easy / medium / hard)

5. Click **Generate**. Wait up to ~60 seconds (Bedrock can be slow).

6. If it works: you’ll see the quiz and can **Download JSON** or **Download DOCX** (or open S3 URL if the Lambda returns one).

## If something fails

**Most common: 403 Forbidden**  
The POST `/generateQuiz` method is using **IAM** (or API Key) auth, so the browser is rejected.

**Fix:** AWS Console → **API Gateway** → open API **yjyn9jsugc** → **Resources** → click **/generateQuiz** → click **POST** → **Method Request** (pencil icon) → set **Authorization** to **NONE** → **Save** → **Actions** → **Deploy API** → stage **prod**. Then try Quiz Generator again.

---

| Symptom | Likely cause | Fix |
|--------|----------------|-----|
| "Failed to fetch" / network error | Wrong URL, CORS, or no route | Check `VITE_API_GATEWAY_URL`; ensure `POST /generateQuiz` exists and OPTIONS returns CORS headers. |
| **403 Forbidden** | Wrong stage name (e.g. `/prod` but API has only `dev`) or method has IAM auth | List stages: `aws apigateway get-stages --rest-api-id yjyn9jsugc --region ap-south-1`. Use that stage in `VITE_API_GATEWAY_URL`. Or set method Authorization to NONE and redeploy. |
| **502 Bad Gateway** | Lambda error (timeout, Bedrock, etc.) | Check CloudWatch log group for `studaxis-quiz-generation-dev`. |
| "API Gateway URL not configured" | Env not set | Set `VITE_API_GATEWAY_URL` in `teacher-dashboard-web/.env` and restart `npm run dev`. |

## Test the endpoint from the command line (optional)

**PowerShell:**

```powershell
$url = "https://yjyn9jsugc.execute-api.ap-south-1.amazonaws.com/dev/generateQuiz"
$body = '{"topic":"Gravity","difficulty":"medium","num_questions":2}'
Invoke-RestMethod -Uri $url -Method POST -Body $body -ContentType "application/json"
```

If you get a JSON payload with `questions` and `quiz_title`, the endpoint and Lambda are working; you can then test from the dashboard.

## Add /generateQuiz to API Gateway (if missing)

If you set up API Gateway from the manual guide and **did not** add quiz:

1. AWS Console → API Gateway → API `yjyn9jsugc`.
2. **Create Resource** → Resource Path: `generateQuiz` → Create.
3. Select the new `/generateQuiz` resource → **Create Method** → choose **POST**.
4. Integration type: **Lambda Function**; Lambda: `studaxis-quiz-generation-dev`; check **Lambda Proxy integration** → Save.
5. **Method Request** → Authorization: **NONE** (for browser calls).
6. Create **OPTIONS** on `/generateQuiz` for CORS (MOCK integration, return 200 with headers `Access-Control-Allow-Origin: *`, `Access-Control-Allow-Methods: POST,OPTIONS`, `Access-Control-Allow-Headers: Content-Type,Authorization`).
7. **Deploy API** → Stage: `prod`.

After that, rerun the dashboard test.
