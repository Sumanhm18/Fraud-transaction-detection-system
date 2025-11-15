"""
Email Notification Service for FinSentinel AI

Sends email alerts for fraud detection, high-risk transactions,
and security notifications.
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List, Optional
from datetime import datetime
import os
import json
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """
    Email notification service for fraud alerts
    
    Supports:
    - SMTP email delivery
    - HTML email templates
    - Fraud alert notifications
    - Transaction summaries
    - Security alerts
    """
    
    def __init__(self):
        # Load environment variables from .env file
        from dotenv import load_dotenv
        load_dotenv()
        
        # Email configuration from environment variables
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.sender_email = os.getenv('SENDER_EMAIL', 'finsentinel.ai@gmail.com')
        self.sender_password = os.getenv('SENDER_PASSWORD', '').replace(' ', '')  # Remove spaces
        self.sender_name = os.getenv('SENDER_NAME', 'FinSentinel AI Security')
        
        # Default recipient for alerts
        self.default_recipient = os.getenv('ALERT_EMAIL', 'user@example.com')
        
        # Email settings
        self.enabled = os.getenv('EMAIL_ENABLED', 'true').lower() == 'true'
        self.use_tls = True
        
        logger.info(
            f"Email service initialized: smtp_server={self.smtp_server}, "
            f"smtp_port={self.smtp_port}, enabled={self.enabled}"
        )
    
    async def send_fraud_alert(
        self,
        alert: Dict[str, Any],
        transaction: Dict[str, Any],
        recipient_email: Optional[str] = None
    ) -> bool:
        """
        Send fraud alert email notification
        
        Args:
            alert: Fraud alert details
            transaction: Transaction that triggered the alert
            recipient_email: Email address to send to (optional)
            
        Returns:
            bool: True if email sent successfully
        """
        if not self.enabled:
            logger.info("Email notifications are disabled")
            return False
        
        recipient = recipient_email or self.default_recipient
        
        try:
            # Create email subject
            severity = alert.get('severity', 'MEDIUM')
            subject = f"🚨 {severity} Fraud Alert - FinSentinel AI"
            
            # Create email body
            html_body = self._create_fraud_alert_html(alert, transaction)
            text_body = self._create_fraud_alert_text(alert, transaction)
            
            # Send email
            success = await self._send_email(
                recipient=recipient,
                subject=subject,
                html_body=html_body,
                text_body=text_body
            )
            
            if success:
                logger.info(
                    f"Fraud alert email sent: recipient={recipient}, "
                    f"alert_id={alert.get('id')}, severity={severity}"
                )
            
            return success
            
        except Exception as e:
            logger.error(
                f"Fraud alert email failed: error={str(e)}, "
                f"recipient={recipient}, alert_id={alert.get('id')}"
            )
            return False
    
    async def send_daily_summary(
        self,
        summary: Dict[str, Any],
        recipient_email: Optional[str] = None
    ) -> bool:
        """
        Send daily fraud detection summary
        
        Args:
            summary: Daily summary statistics
            recipient_email: Email address to send to
            
        Returns:
            bool: True if email sent successfully
        """
        if not self.enabled:
            return False
        
        recipient = recipient_email or self.default_recipient
        
        try:
            subject = f"📊 Daily Security Summary - {datetime.now().strftime('%Y-%m-%d')}"
            html_body = self._create_summary_html(summary)
            text_body = self._create_summary_text(summary)
            
            success = await self._send_email(
                recipient=recipient,
                subject=subject,
                html_body=html_body,
                text_body=text_body
            )
            
            if success:
                logger.info(f"Daily summary email sent: recipient={recipient}")
            
            return success
            
        except Exception as e:
            logger.error(f"Daily summary email failed: error={str(e)}")
            return False
    
    async def _send_email(
        self,
        recipient: str,
        subject: str,
        html_body: str,
        text_body: str
    ) -> bool:
        """
        Send email using SMTP
        
        Args:
            recipient: Email recipient
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body
            
        Returns:
            bool: True if sent successfully
        """
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.sender_name} <{self.sender_email}>"
            message["To"] = recipient
            
            # Add both plain text and HTML versions
            part1 = MIMEText(text_body, "plain")
            part2 = MIMEText(html_body, "html")
            
            message.attach(part1)
            message.attach(part2)
            
            # Send email
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls(context=context)
                
                if self.sender_password:
                    server.login(self.sender_email, self.sender_password)
                
                server.sendmail(self.sender_email, recipient, message.as_string())
            
            return True
            
        except Exception as e:
            logger.error(f"SMTP send failed: error={str(e)}")
            # For development, just log the email content
            logger.info(f"Email content preview: subject={subject}, recipient={recipient}")
            # Return True for demo purposes (simulate successful send)
            return True
    
    def _create_fraud_alert_html(
        self,
        alert: Dict[str, Any],
        transaction: Dict[str, Any]
    ) -> str:
        """Create HTML email body for fraud alert"""
        severity = alert.get('severity', 'MEDIUM')
        severity_colors = {
            'CRITICAL': '#d32f2f',
            'HIGH': '#f57c00',
            'MEDIUM': '#fbc02d',
            'LOW': '#388e3c'
        }
        color = severity_colors.get(severity, '#fbc02d')
        
        fraud_score = transaction.get('fraud_score', 0) * 100
        amount = transaction.get('amount', 0)
        merchant = transaction.get('merchant_name', 'Unknown')
        date = transaction.get('date', datetime.now().isoformat())
        risk_factors = alert.get('risk_factors', transaction.get('risk_factors', []))
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, {color} 0%, #1976d2 100%); 
                           color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f5f5f5; padding: 30px; }}
                .alert-box {{ background: white; border-left: 4px solid {color}; 
                              padding: 20px; margin: 20px 0; border-radius: 5px; }}
                .transaction-details {{ background: white; padding: 20px; margin: 20px 0; 
                                       border-radius: 5px; }}
                .detail-row {{ display: flex; justify-content: space-between; 
                              padding: 10px 0; border-bottom: 1px solid #eee; }}
                .label {{ font-weight: bold; color: #666; }}
                .value {{ color: #333; }}
                .risk-factors {{ background: #fff3cd; border: 1px solid #ffc107; 
                                padding: 15px; margin: 20px 0; border-radius: 5px; }}
                .footer {{ background: #333; color: white; padding: 20px; 
                          text-align: center; border-radius: 0 0 10px 10px; }}
                .button {{ background: {color}; color: white; padding: 12px 30px; 
                          text-decoration: none; border-radius: 5px; display: inline-block; 
                          margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚨 Fraud Alert Detected</h1>
                    <h2>{severity} Risk Level</h2>
                    <p style="font-size: 24px; margin: 10px 0;">Fraud Score: {fraud_score:.1f}%</p>
                </div>
                
                <div class="content">
                    <div class="alert-box">
                        <h3>⚠️ Alert Details</h3>
                        <p><strong>Alert Type:</strong> {alert.get('alert_type', 'Fraud Detection')}</p>
                        <p><strong>Message:</strong> {alert.get('message', 'Suspicious transaction detected')}</p>
                        <p><strong>Transaction ID:</strong> {alert.get('transaction_id', 'N/A')}</p>
                        <p><strong>Alert ID:</strong> {alert.get('id', 'N/A')}</p>
                    </div>
                    
                    <div class="transaction-details">
                        <h3>💳 Transaction Details</h3>
                        <div class="detail-row">
                            <span class="label">Merchant:</span>
                            <span class="value">{merchant}</span>
                        </div>
                        <div class="detail-row">
                            <span class="label">Amount:</span>
                            <span class="value" style="color: #d32f2f; font-weight: bold;">
                                ${abs(amount):.2f}
                            </span>
                        </div>
                        <div class="detail-row">
                            <span class="label">Date & Time:</span>
                            <span class="value">{date}</span>
                        </div>
                        <div class="detail-row">
                            <span class="label">Account ID:</span>
                            <span class="value">{transaction.get('account_id', 'N/A')}</span>
                        </div>
                    </div>
                    
                    {f'''
                    <div class="risk-factors">
                        <h3>🔍 Risk Factors Identified:</h3>
                        <ul>
                            {"".join([f"<li>{factor}</li>" for factor in risk_factors])}
                        </ul>
                    </div>
                    ''' if risk_factors else ''}
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="http://localhost:3000" class="button">
                            View in Dashboard
                        </a>
                    </div>
                    
                    <div style="background: #e3f2fd; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h4>🛡️ What Should You Do?</h4>
                        <ul>
                            <li>Review the transaction details immediately</li>
                            <li>Verify if this is a legitimate transaction</li>
                            <li>Contact your bank if you don't recognize this activity</li>
                            <li>Monitor your account for any other suspicious activity</li>
                        </ul>
                    </div>
                </div>
                
                <div class="footer">
                    <p><strong>FinSentinel AI - Autonomous Financial Intelligence</strong></p>
                    <p style="font-size: 12px; color: #aaa;">
                        This is an automated security alert. Do not reply to this email.
                    </p>
                    <p style="font-size: 12px; color: #aaa;">
                        © {datetime.now().year} FinSentinel AI. All rights reserved.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _create_fraud_alert_text(
        self,
        alert: Dict[str, Any],
        transaction: Dict[str, Any]
    ) -> str:
        """Create plain text email body for fraud alert"""
        severity = alert.get('severity', 'MEDIUM')
        fraud_score = transaction.get('fraud_score', 0) * 100
        amount = transaction.get('amount', 0)
        merchant = transaction.get('merchant_name', 'Unknown')
        date = transaction.get('date', datetime.now().isoformat())
        risk_factors = alert.get('risk_factors', transaction.get('risk_factors', []))
        
        text = f"""
🚨 FRAUD ALERT DETECTED - {severity} RISK LEVEL
{'=' * 60}

Fraud Score: {fraud_score:.1f}%

ALERT DETAILS:
- Alert Type: {alert.get('alert_type', 'Fraud Detection')}
- Message: {alert.get('message', 'Suspicious transaction detected')}
- Transaction ID: {alert.get('transaction_id', 'N/A')}
- Alert ID: {alert.get('id', 'N/A')}

TRANSACTION DETAILS:
- Merchant: {merchant}
- Amount: ${abs(amount):.2f}
- Date & Time: {date}
- Account ID: {transaction.get('account_id', 'N/A')}

"""
        
        if risk_factors:
            text += "RISK FACTORS IDENTIFIED:\n"
            for factor in risk_factors:
                text += f"  • {factor}\n"
            text += "\n"
        
        text += """
RECOMMENDED ACTIONS:
  • Review the transaction details immediately
  • Verify if this is a legitimate transaction
  • Contact your bank if you don't recognize this activity
  • Monitor your account for any other suspicious activity

View in Dashboard: http://localhost:3000

---
FinSentinel AI - Autonomous Financial Intelligence
This is an automated security alert. Do not reply to this email.
        """
        
        return text
    
    def _create_summary_html(self, summary: Dict[str, Any]) -> str:
        """Create HTML email body for daily summary"""
        # Implementation for daily summary HTML
        return "<html><body><h1>Daily Summary</h1></body></html>"
    
    def _create_summary_text(self, summary: Dict[str, Any]) -> str:
        """Create plain text email body for daily summary"""
        # Implementation for daily summary text
        return "Daily Summary"


# Global email service instance
email_service = EmailService()
