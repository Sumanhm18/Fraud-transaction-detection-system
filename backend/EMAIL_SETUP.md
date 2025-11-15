# Email Notification API Endpoint

POST /api/v1/email/test

- Test email notification
- Request Body: { "email": "user@example.com" }

POST /api/v1/email/configure

- Update email settings
- Request Body: {
  "recipient_email": "user@example.com",
  "enabled": true
  }

GET /api/v1/email/status

- Check email service status
- Returns: { "enabled": true, "configured": true }

## Email Configuration

To enable email notifications:

1. Set environment variables in `.env`:

   ```
   EMAIL_ENABLED=true
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SENDER_EMAIL=your-email@gmail.com
   SENDER_PASSWORD=your-app-password
   ALERT_EMAIL=recipient@example.com
   ```

2. For Gmail:

   - Enable 2-factor authentication
   - Generate App Password: https://myaccount.google.com/apppasswords
   - Use the App Password as SENDER_PASSWORD

3. Fraud alerts will be sent automatically when:
   - Fraud score > 0.6 (High/Critical risk)
   - Transaction shows suspicious patterns
   - Risk factors are detected

## Email Features

✅ Beautiful HTML email templates
✅ Plain text fallback
✅ Color-coded severity levels
✅ Transaction details
✅ Risk factor breakdown
✅ Action recommendations
✅ Direct dashboard link
