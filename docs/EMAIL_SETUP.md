# Email codes on the free deployment

Email codes, password recovery, and public registration need a working SMTP
account. Administrator-created teammate accounts work without SMTP at
**User Management → Create User**. Use a real, accessible email address for
any account that will enable email verification.

Render Free blocks outbound SMTP ports **25, 465, and 587**. A normal Gmail
SMTP configuration on port 587 will therefore fail on this service. Use a
provider supporting **2525 with STARTTLS**, such as Brevo. Its Free plan has a
daily email quota; account approval and sender verification still apply.

1. In your email provider, verify your sender address and enable transactional
   sending. In Brevo, open **SMTP & API → SMTP**. Copy the **SMTP login** and
   generate an **SMTP key** privately. An API key or your account password is
   not the SMTP key.
2. Open [Render environment settings](https://dashboard.render.com/web/srv-dbtiislg1s2s73b7jca0/env).
   Add the following environment variables. Replace the two credential
   placeholders and sender placeholder privately; never commit them or paste
   them into chat.

   ```dotenv
   SMTP_HOST=smtp-relay.brevo.com
   SMTP_PORT=2525
   SMTP_USERNAME=YOUR_PROVIDER_SMTP_LOGIN
   SMTP_PASSWORD=YOUR_PROVIDER_SMTP_KEY
   SMTP_FROM_EMAIL=YOUR_VERIFIED_SENDER_EMAIL
   SMTP_FROM_NAME=ZUKA Security Operations Center
   SMTP_USE_TLS=true
   SMTP_USE_SSL=false
   FRONTEND_BASE_URL=https://zuka-soc.onrender.com
   ```

3. Save the variables and choose **Manual Deploy → Deploy latest commit** once
   GitHub checks pass. Keep your existing database and JWT/OTP signing secrets.
4. Sign in, open **Settings → Security & Sessions → Two-step verification →
   Enable**, then enter the code from your account email. Confirm **Enabled**.
   Sign out and sign in again to test the email challenge. Check your spam
   folder and provider's transactional logs if no code arrives. Do not enable
   this on the owner account until delivery succeeds.

Tests exercise OTP setup/login with captured mail and verify the STARTTLS 2525
transport configuration. They do not prove delivery from your production SMTP
account; that requires the private configuration and an actual received code.

References: [Render Free limitations](https://render.com/docs/free),
[Brevo SMTP credentials](https://developers.brevo.com/docs/smtp-integration),
[Brevo ports and STARTTLS](https://help.brevo.com/hc/en-us/articles/10905415650322-Which-SMTP-port-should-I-use-Port-587-465-or-2525).
