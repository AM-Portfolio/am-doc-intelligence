# Gmail OAuth Setup Guide

This guide will walk you through setting up Google OAuth credentials for the email extractor application.

## Prerequisites

- Google Account
- Access to Google Cloud Console

## Step-by-Step Instructions

### 1. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click on the project dropdown at the top
3. Click "New Project"
4. Enter a project name (e.g., "Email Extractor")
5. Click "Create"

### 2. Enable Gmail API

1. In your project, go to "APIs & Services" > "Library"
2. Search for "Gmail API"
3. Click on "Gmail API"
4. Click "Enable"

### 3. Configure OAuth Consent Screen

1. Go to "APIs & Services" > "OAuth consent screen"
2. Select "External" user type (unless you have Google Workspace)
3. Click "Create"
4. Fill in the required fields:
   - **App name**: Email Extractor
   - **User support email**: Your email
   - **Developer contact information**: Your email
5. Click "Save and Continue"
6. On "Scopes" page, click "Save and Continue" (we'll use default scopes)
7. On "Test users" page, add your email address as a test user
8. Click "Save and Continue"

### 4. Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Select "Web application" as application type
4. Enter a name (e.g., "Email Extractor Web Client")
5. Under "Authorized redirect URIs", add:
   - `http://localhost:5000/gmail/callback`
   - `http://127.0.0.1:5000/gmail/callback`
6. Click "Create"
7. A dialog will show your **Client ID** and **Client Secret**
8. **IMPORTANT**: Copy both values - you'll need them next!

### 5. Configure Application

#### Option A: Using .env file (Recommended)

1. Create a file named `.env` in your project root directory
2. Add the following content:

```
GOOGLE_CLIENT_ID=your-client-id-here
GOOGLE_CLIENT_SECRET=your-client-secret-here
SESSION_SECRET=your-random-secret-key-here
```

3. Replace `your-client-id-here` with your actual Client ID
4. Replace `your-client-secret-here` with your actual Client Secret
5. Replace `your-random-secret-key-here` with a random string (for session encryption)

#### Option B: Using Environment Variables

**Windows PowerShell** (Permanent):
```powershell
[System.Environment]::SetEnvironmentVariable('GOOGLE_CLIENT_ID', 'your-client-id-here', 'User')
[System.Environment]::SetEnvironmentVariable('GOOGLE_CLIENT_SECRET', 'your-client-secret-here', 'User')
```

After setting environment variables, restart your terminal/PowerShell.

### 6. Install Required Dependencies

If using .env file, install python-dotenv:

```bash
pip install python-dotenv
```

Or add to `pyproject.toml`:
```toml
dependencies = [
    ...
    "python-dotenv>=1.0.0"
]
```

### 7. Start the Application

```bash
python app.py
```

### 8. Test Gmail Integration

1. Open browser to `http://127.0.0.1:5000/gmail`
2. Click "Connect Gmail" button
3. Sign in with your Google account
4. Grant permissions when prompted
5. You should be redirected back to the application
6. Gmail should now be connected!

## Troubleshooting

### Error: "Gmail credentials not found in environment variables"

- Make sure you've set the environment variables correctly
- If using .env file, ensure it's in the project root directory
- Restart the Flask application after setting variables

### Error: "redirect_uri_mismatch"

- Ensure the redirect URI in Google Cloud Console matches exactly:
  - `http://localhost:5000/gmail/callback` or
  - `http://127.0.0.1:5000/gmail/callback`
- Check that you're accessing the app using the same URL

### Error: "Access blocked: This app's request is invalid"

- Make sure you've added your email as a test user in OAuth consent screen
- Verify Gmail API is enabled for your project

### Error: "The client application is not authorized"

- Your OAuth consent screen might still be in "Testing" mode
- Add your Google account to the test users list

## Security Notes

⚠️ **IMPORTANT**: 
- Never commit your `.env` file to version control
- Keep your Client Secret confidential
- Add `.env` to your `.gitignore` file
- For production deployment, use environment variables or secure secret management

## Additional Resources

- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Gmail API Documentation](https://developers.google.com/gmail/api/guides)
