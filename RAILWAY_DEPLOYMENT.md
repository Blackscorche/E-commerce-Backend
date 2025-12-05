# Railway Deployment Guide

This guide will help you deploy your Django eCommerce backend to Railway.

## Prerequisites

1. A Railway account (sign up at [railway.app](https://railway.app))
2. Your backend code pushed to a Git repository (GitHub, GitLab, or Bitbucket)
3. Your Paystack API keys (if using payments)
4. AWS credentials (if using S3 for media/static files in production)

## Important: Dependencies Installation

Railway will automatically detect and install dependencies from `requirements.txt` at the root of your project. This file has been created for Railway deployment.

## Step-by-Step Deployment

### 1. Create a New Project on Railway

1. Go to [railway.app](https://railway.app) and sign in
2. Click "New Project"
3. Select "Deploy from GitHub repo" (or your Git provider)
4. Select your `E-commerce-Backend` repository
5. Railway will automatically detect it's a Python project

### 2. Add PostgreSQL Database

1. In your Railway project dashboard, click "+ New"
2. Select "Database" → "Add PostgreSQL"
3. Railway will automatically create a PostgreSQL database
4. The database connection variables will be automatically set as environment variables:
   - `POSTGRES_HOST`
   - `POSTGRES_PORT`
   - `POSTGRES_DB`
   - `POSTGRES_USER`
   - `POSTGRES_PASSWORD`

### 3. Configure Environment Variables

In your Railway project settings, go to "Variables" and add the following:

#### Required Variables:

```bash
# Environment
PROJECT_ENVIRONMENT=production

# Django
DJANGO_SECRET_KEY=your-secret-key-here  # Generate a strong secret key
DJANGO_SETTINGS_MODULE=src.settings.defaults

# CORS - Your frontend URL
CORS_ALLOWED_ORIGINS=https://e-commerce-frontend-lyart-seven.vercel.app

# Frontend URL for callbacks
FRONTEND_URL=https://e-commerce-frontend-lyart-seven.vercel.app

# Allowed Hosts (Railway will provide your app URL, add it here)
ALLOWED_HOSTS=your-app-name.railway.app,*.railway.app
```

#### Paystack (Required for payments):

```bash
PAYSTACK_SECRET_KEY=sk_test_...  # Your Paystack secret key
PAYSTACK_PUBLIC_KEY=pk_test_...  # Your Paystack public key
PAYSTACK_WEBHOOK_SECRET=your-webhook-secret  # Optional, defaults to secret key
```

#### AWS S3 (Required for production media/static files):

```bash
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_STORAGE_BUCKET_NAME=your-bucket-name
```

**Note:** Railway automatically provides PostgreSQL connection variables, so you don't need to set `POSTGRES_*` variables manually.

### 4. Update Allowed Hosts

After Railway deploys your app, you'll get a URL like `your-app-name.railway.app`. 

1. Copy your Railway app URL
2. Go to Railway project → Settings → Variables
3. Update `ALLOWED_HOSTS` to include your Railway URL:
   ```
   ALLOWED_HOSTS=your-app-name.railway.app,*.railway.app
   ```

### 5. Deploy

1. Railway will automatically deploy when you push to your main branch
2. Or click "Deploy" in the Railway dashboard
3. Wait for the deployment to complete
4. Check the logs to ensure migrations ran successfully

### 6. Get Your Backend URL

Once deployed, Railway will provide you with a URL like:
```
https://your-app-name.railway.app
```

Your API will be available at:
```
https://your-app-name.railway.app/api/
```

### 7. Update Frontend Configuration

Update your frontend's `backend_url.ts` file:

```typescript
export const API_PATH = "https://your-app-name.railway.app/api/";
```

Then redeploy your frontend to Vercel.

## Environment Variables Summary

Here's a complete list of all environment variables you need to set in Railway:

| Variable | Description | Example |
|----------|-------------|---------|
| `PROJECT_ENVIRONMENT` | Set to "production" | `production` |
| `DJANGO_SECRET_KEY` | Django secret key | Generate a secure key |
| `DJANGO_SETTINGS_MODULE` | Django settings module | `src.settings.defaults` |
| `CORS_ALLOWED_ORIGINS` | Frontend URL(s) | `https://e-commerce-frontend-lyart-seven.vercel.app` |
| `FRONTEND_URL` | Frontend URL for callbacks | `https://e-commerce-frontend-lyart-seven.vercel.app` |
| `ALLOWED_HOSTS` | Allowed hostnames | `your-app-name.railway.app,*.railway.app` |
| `PAYSTACK_SECRET_KEY` | Paystack secret key | `sk_test_...` |
| `PAYSTACK_PUBLIC_KEY` | Paystack public key | `pk_test_...` |
| `PAYSTACK_WEBHOOK_SECRET` | Paystack webhook secret | Optional |
| `AWS_ACCESS_KEY_ID` | AWS access key | Your AWS key |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Your AWS secret |
| `AWS_STORAGE_BUCKET_NAME` | S3 bucket name | `your-bucket-name` |

**Note:** PostgreSQL variables (`POSTGRES_HOST`, `POSTGRES_PORT`, etc.) are automatically provided by Railway when you add a PostgreSQL service.

## Generating a Django Secret Key

To generate a secure Django secret key, run:

```python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Or use an online generator: https://djecrety.ir/

## Troubleshooting

### Database Connection Issues
- Ensure PostgreSQL service is added and running
- Check that database variables are set correctly
- Verify migrations ran successfully in the logs

### CORS Errors
- Ensure `CORS_ALLOWED_ORIGINS` includes your frontend URL
- Check that `ALLOWED_HOSTS` includes your Railway domain
- Verify the frontend is using the correct backend URL

### Static/Media Files Not Loading
- Ensure AWS S3 credentials are set correctly
- Verify `AWS_STORAGE_BUCKET_NAME` is correct
- Check that files are uploaded to S3

### App Not Starting
- Check Railway logs for errors
- Verify all required environment variables are set
- Ensure `Procfile` or `railway.toml` is configured correctly

## Monitoring

- Check Railway dashboard for deployment status
- View logs in Railway dashboard → Deployments → View Logs
- Monitor resource usage in Railway dashboard

## Next Steps

1. Set up a custom domain (optional) in Railway settings
2. Configure webhooks for Paystack payments
3. Set up monitoring and alerts
4. Configure backups for PostgreSQL database

