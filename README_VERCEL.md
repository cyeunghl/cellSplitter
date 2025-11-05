# Vercel Deployment Guide

This Flask application is configured for deployment on Vercel.

## Files for Vercel

- `vercel.json` - Vercel configuration
- `api/index.py` - Serverless function entry point
- `.vercelignore` - Files to exclude from deployment
- `requirements.txt` - Python dependencies

## Deployment Steps

1. Install Vercel CLI (if not already installed):
   ```bash
   npm i -g vercel
   ```

2. Login to Vercel:
   ```bash
   vercel login
   ```

3. Deploy:
   ```bash
   vercel
   ```

4. For production deployment:
   ```bash
   vercel --prod
   ```

## Important Notes

### Database Storage
- The app uses SQLite stored in `/tmp` directory on Vercel
- **Data will NOT persist across deployments** - `/tmp` is ephemeral
- For production, consider using:
  - Vercel Postgres
  - Supabase
  - PlanetScale
  - Or another managed database service

### Environment Variables
Set these in Vercel dashboard under Project Settings > Environment Variables:
- `SECRET_KEY` - Flask secret key (generate a secure random string)
- `VERCEL` or `VERCEL_ENV` - Automatically set by Vercel

### Static Files
Static files in `/static` are automatically served by Vercel with caching headers.

## Troubleshooting

- If you see import errors, ensure `app.py` is in the root directory
- Database initialization happens automatically on first request
- Check Vercel function logs for any errors

