import os
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from fastapi import BackgroundTasks
from typing import Optional

    
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_PORT=int(os.getenv("MAIL_PORT")),
    MAIL_SERVER=os.getenv("MAIL_SERVER"),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

async def send_verification_email(
    email: str,
    name: str,
    token: str,
    redirect_url: str,
    background_tasks: BackgroundTasks,
    password: Optional[str] = None,
):
    

    verification_url = f"{redirect_url}?token={token}"

    logo_url = "https://res.cloudinary.com/mano22/image/upload/v1751216813/logo_bkxcak.png"
    
    temp_password_html = ""
    if password:
        temp_password_html = f"""
            <tr>
                <td style="padding: 8px 0; color: #7f8c8d;">Temporary Password:</td>
                <td style="padding: 8px 0;">
                    <span style="background-color: #fff2f2; color: #e74c3c; padding: 4px 8px; border-radius: 4px; font-family: monospace; font-size: 1.1em;">
                        {password}
                    </span>
                </td>
            </tr>
        """

    message = MessageSchema(
    subject="Your OTSEC-HUB Account Credentials",
    recipients=[email],
    body=f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
        <!-- Email Header -->
        <div style="background: linear-gradient(135deg, #28a745 0%, #2a5233 100%); padding: 20px 20px; text-align: center; color: white;">
            <img src="{logo_url}" alt="OTSEC-HUB Logo" style="height: 60px; margin-bottom: 15px;">
            <h1 style="margin: 0; font-weight: 300;">Account Setup</h1>
        </div>
        
        <!-- Main Content -->
        <div style="padding: 30px; background-color: #ffffff;">
            <h2 style="color: #28a745; margin-top: 0;">Welcome, {name}!</h2>
            <p style="font-size: 16px; color: black; line-height: 1.6;">Your OTSEC-HUB account has been created. Click the button below to activate your account.</p>
            
            <!-- Credentials Box -->
            <div style="background-color: #f8f9fa; border-radius: 8px; padding: 20px; margin: 25px 0; border-left: 5px solid #2a5233;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="width: 30%; padding: 8px 0; color: #7f8c8d;">Email:</td>
                        <td style="padding: 8px 0; font-weight: 500;">{email}</td>
                    </tr>
                    {temp_password_html}
                    
                </table>
            </div>
            
            <!-- Action Button -->
            <div style="text-align: center; margin: 30px 0;">
                <a href="{verification_url}" style="
                    background: linear-gradient(to right, #2a5233, #28a745);
                    color: white;
                    padding: 14px 28px;
                    text-decoration: none;
                    border-radius: 30px;
                    font-weight: bold;
                    font-size: 16px;
                    display: inline-block;
                    box-shadow: 0 4px 8px rgba(52, 152, 219, 0.3);
                    transition: all 0.3s ease;
                " onmouseover="this.style.opacity='0.8'" onmouseout="this.style.opacity='1'">
                    Activate Your Account
                </a>
            </div>
            
        </div>

        <!-- Footer -->
        <div style="background-color: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #7f8c8d; border-top: 1px solid #e0e0e0;">
            <p style="margin: 0;">©OTSEC-HUB. All rights reserved.</p>
            <p style="margin: 5px 0 0;">Need help? <a href="mailto:support@otsec-hub.edu" style="color: #2a5233;">Contact our support team</a></p>
        </div>
                <p style="color:red; margin:15px 0px"> This email is designated as a no-reply email, and any replies to this message will not receive responses. </p> 
    </div>
    """,
    subtype="html"
)
    
    fm = FastMail(conf)
    background_tasks.add_task(fm.send_message, message)


async def send_email_change_verification(
    email: str,
    name: str,
    token: str,
    redirect_url: str,
    background_tasks: BackgroundTasks,
):
    verification_url = f"{redirect_url}?token={token}"
    logo_url = "https://res.cloudinary.com/mano22/image/upload/v1751216813/logo_bkxcak.png"

    message = MessageSchema(
        subject="Confirm your new OTSEC-HUB email",
        recipients=[email],
        body=f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
        <div style="background: linear-gradient(135deg, #28a745 0%, #2a5233 100%); padding: 20px 20px; text-align: center; color: white;">
            <img src="{logo_url}" alt="OTSEC-HUB Logo" style="height: 60px; margin-bottom: 15px;">
            <h1 style="margin: 0; font-weight: 300;">Email Change</h1>
        </div>

        <div style="padding: 30px; background-color: #ffffff;">
            <h2 style="color: #28a745; margin-top: 0;">Hello, {name}!</h2>
            <p style="font-size: 16px; color: black; line-height: 1.6;">You asked to change the email on your OTSEC-HUB account. Click the button below to confirm this new address. Your current email stays active until you confirm.</p>

            <div style="background-color: #f8f9fa; border-radius: 8px; padding: 20px; margin: 25px 0; border-left: 5px solid #2a5233;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="width: 30%; padding: 8px 0; color: #7f8c8d;">New Email:</td>
                        <td style="padding: 8px 0; font-weight: 500;">{email}</td>
                    </tr>
                </table>
            </div>

            <div style="text-align: center; margin: 30px 0;">
                <a href="{verification_url}" style="
                    background: linear-gradient(to right, #2a5233, #28a745);
                    color: white;
                    padding: 14px 28px;
                    text-decoration: none;
                    border-radius: 30px;
                    font-weight: bold;
                    font-size: 16px;
                    display: inline-block;
                    box-shadow: 0 4px 8px rgba(52, 152, 219, 0.3);
                    transition: all 0.3s ease;
                " onmouseover="this.style.opacity='0.8'" onmouseout="this.style.opacity='1'">
                    Confirm New Email
                </a>
            </div>
        </div>

        <div style="background-color: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #7f8c8d; border-top: 1px solid #e0e0e0;">
            <p style="margin: 0;">©OTSEC-HUB. All rights reserved.</p>
            <p style="margin: 5px 0 0;">Need help? <a href="mailto:support@otsec-hub.edu" style="color: #2a5233;">Contact our support team</a></p>
        </div>
                <p style="color:red; margin:15px 0px"> This email is designated as a no-reply email, and any replies to this message will not receive&nbsp;responses. </p>
    </div>
    """,
        subtype="html",
    )

    fm = FastMail(conf)
    background_tasks.add_task(fm.send_message, message)


async def send_educator_invite_email(
    email: str,
    name: str,
    token: str,
    redirect_url: str,
    background_tasks: BackgroundTasks,
):
    verification_url = f"{redirect_url}?token={token}"
    logo_url = "https://res.cloudinary.com/mano22/image/upload/v1751216813/logo_bkxcak.png"

    message = MessageSchema(
        subject="Your OTSEC-HUB educator invitation",
        recipients=[email],
        body=f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
        <div style="background: linear-gradient(135deg, #28a745 0%, #2a5233 100%); padding: 20px 20px; text-align: center; color: white;">
            <img src="{logo_url}" alt="OTSEC-HUB Logo" style="height: 60px; margin-bottom: 15px;">
            <h1 style="margin: 0; font-weight: 300;">Educator Invitation</h1>
        </div>

        <div style="padding: 30px; background-color: #ffffff;">
            <h2 style="color: #28a745; margin-top: 0;">Welcome, {name}!</h2>
            <p style="font-size: 16px; color: black; line-height: 1.6;">You are invited to join OTSEC-HUB as an educator and share your learning with the community. Click the button below to choose your password and activate your account.</p>

            <div style="background-color: #f8f9fa; border-radius: 8px; padding: 20px; margin: 25px 0; border-left: 5px solid #2a5233;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="width: 30%; padding: 8px 0; color: #7f8c8d;">Email:</td>
                        <td style="padding: 8px 0; font-weight: 500;">{email}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #7f8c8d;">Role:</td>
                        <td style="padding: 8px 0; font-weight: 500;">Educator</td>
                    </tr>
                </table>
            </div>

            <div style="text-align: center; margin: 30px 0;">
                <a href="{verification_url}" style="
                    background: linear-gradient(to right, #2a5233, #28a745);
                    color: white;
                    padding: 14px 28px;
                    text-decoration: none;
                    border-radius: 30px;
                    font-weight: bold;
                    font-size: 16px;
                    display: inline-block;
                    box-shadow: 0 4px 8px rgba(52, 152, 219, 0.3);
                    transition: all 0.3s ease;
                " onmouseover="this.style.opacity='0.8'" onmouseout="this.style.opacity='1'">
                    Set Up Your Account
                </a>
            </div>
        </div>

        <div style="background-color: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #7f8c8d; border-top: 1px solid #e0e0e0;">
            <p style="margin: 0;">©OTSEC-HUB. All rights reserved.</p>
            <p style="margin: 5px 0 0;">Need help? <a href="mailto:support@otsec-hub.edu" style="color: #2a5233;">Contact our support team</a></p>
        </div>
                <p style="color:red; margin:15px 0px"> This email is designated as a no-reply email, and any replies to this message will not receive&nbsp;responses. </p>
    </div>
    """,
        subtype="html",
    )

    fm = FastMail(conf)
    background_tasks.add_task(fm.send_message, message)