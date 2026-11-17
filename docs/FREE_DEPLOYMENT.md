# Free website and database

Current deployment: [zuka-soc.onrender.com](https://zuka-soc.onrender.com).

Use one **Render Free web service** for the built React website and Python API,
and one **Neon Free PostgreSQL project** for persistent records. The offline
assistant needs no paid AI service. Never select a paid plan or attach a card
just to follow this guide.

Render provides an HTTPS `*.onrender.com` address. Request service name
`zuka-soc`; the actual hostname depends on availability and appears in the
Render dashboard. A custom `.com` domain is a separate purchase. Do not claim
that a hostname is live until Render has created it and its checks pass.

## Database

1. In Neon, create a Free project named `zuka-soc`, using PostgreSQL 16 or later.
2. Choose a region near the Render service. Create a dedicated empty `zuka_soc`
   database. Do not reuse an existing account database for tests.
3. Copy its SSL connection URL from Neon's Connect dialog directly into Render's
   secret environment setting `DATABASE_URL`. Never paste it into an issue,
   screenshot, chat, or committed file. Standard `postgresql://` URLs are
   normalized by the application.

## Website and API

1. In Render, choose New → Blueprint and connect this GitHub repository.
2. Select `main` and the root `render.yaml`. Confirm the web service plan says
   **Free**. This blueprint intentionally creates no Render database; Render's
   free database expires after 30 days.
3. Supply `DATABASE_URL`, your private `BOOTSTRAP_ADMIN_EMAIL`, and a strong
   unique `BOOTSTRAP_ADMIN_PASSWORD`. Render generates different JWT and OTP
   secrets. Keep the same signing secrets across deployments.
4. Keep `ENABLE_IN_PROCESS_REPLAY=false`, `ZUKA_LLM_PROVIDER=disabled`, and
   `RAG_GENERATION_ENABLED=false`. `SEED_DEMO_DATA=true` imports the included
   65-row sample once when the event table is empty. All displayed traffic is
   research dataset replay.
5. Deploy after GitHub checks pass. Startup applies migrations and creates the
   administrator only if its email does not exist. No default password exists.
6. Open the actual Render URL. Check `/api/health` and `/api/ready`, sign in,
   inspect each screen, test the assistant, and generate a PDF. Verify access
   from a phone. Save the URL after these checks succeed.
7. Remove bootstrap password/email variables after successful initialization.
   They are not needed for normal restarts. Store the owner password privately.

The container serves website deep links and API requests on the same origin;
no separate frontend service, CORS setup, or paid static-site host is needed.

If creating a service from a public repository URL instead of a Blueprint, use
Render's **Manual Deploy → Deploy latest commit** after GitHub checks pass.
Automatic Git deployments require the supported provider/Blueprint connection.

## Optional services and limits

SMTP is needed for email verification, self-registration, password recovery, and
email two-factor authentication. These unavailable actions are hidden/disabled
when SMTP is absent. An administrator can create teammate app accounts. Real
SMTP and browser push delivery are not covered by the mocked-email tests.
For email codes on Render Free, follow [Email setup](EMAIL_SETUP.md): ports
25, 465, and 587 are blocked; use an SMTP provider supporting STARTTLS on 2525.

In **Network Monitor**, administrators and analysts can choose **Process next
demo event**. This processes one row of the included sample, saves its network
flow, and creates an alert, incident, and real TreeSHAP explanation when the
model predicts an attack. Benign predictions create only the flow record.
Older alerts offer **Generate explanation**. Explanations require retained
inputs or an unambiguous match to the included sample and stored replay
evidence; reconstructed inputs are explicitly labeled. Unknown legacy alerts
remain without an explanation rather than receiving invented evidence.

Free web services sleep after inactivity and may take time to wake. Free compute,
storage, transfer, and build quotas can suspend service when exhausted. Monitor
both dashboards; do not enable automatic paid upgrades. Render's free filesystem
is ephemeral: PostgreSQL holds account and SOC records, while the local knowledge
index can be regenerated. Reports are generated from database records.

This is a public demonstration deployment, with recorded defense plans rather
than live firewall enforcement. Free tiers are unsuitable for an always-on SOC
with availability commitments. Maintain database exports/backups and verify a
restore before entrusting irreplaceable records.

Primary provider references: [Render Free](https://render.com/docs/free),
[Render Blueprints](https://render.com/docs/blueprint-spec),
[Neon Free plan](https://neon.com/blog/neon-free-plan-1-gb-per-project).
