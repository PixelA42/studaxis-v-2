# AppSync API Key — One-Time Setup

The student app needs an API key to call AppSync. **The key value is only shown once when you create it.**

## Steps

1. Open: [AppSync Console → studaxis-graphql-api → Settings](https://ap-south-1.console.aws.amazon.com/appsync/home?region=ap-south-1#/z6rvf6on6jhblds7udlfnm5i4e/settings)

2. Scroll to **API Keys** → **Create API key**

3. (Optional) Set expiry (default 7 days; max 365 days)

4. Click **Create** — **copy the key value immediately** (it won’t be shown again)

5. Paste into `backend/.env`:
   ```
   APPSYNC_API_KEY=da2-xxxxxxxxxxxxxxxxxxxxxxxx
   ```

6. Restart the FastAPI backend so it loads the new env.
