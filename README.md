# Route 53 DNS Updater

A Docker-based dynamic DNS updater for AWS Route 53 that automatically updates A and AAAA records when your public IP changes.

## Features

- Dual-source IP validation (checkip.amazonaws.com + icanhazip.com)
- Updates Route 53 A (IPv4) and/or AAAA (IPv6) records
- Runs continuously with configurable check interval (default: 5 minutes)
- Built-in security: IP format validation, rate limiting, input sanitization
- Fully configurable via docker-compose.yml

## Prerequisites

- Docker (with Compose V2) installed on your system
- An AWS account with a domain in Route 53
- Basic command line knowledge

---

## Complete Setup Guide

### Step 1: Get the Files

You have two options:

#### Option A: Clone from GitHub (Recommended)

```bash
# Clone the repository
git clone https://github.com/c1aytonnet/route53-updater.git

# Navigate into the folder
cd route53-updater
```

#### Option B: Download Manually

1. Go to https://github.com/c1aytonnet/route53-updater
2. Click the green **"Code"** button
3. Click **"Download ZIP"**
4. Extract the ZIP file
5. Open Terminal and navigate to the extracted folder:
   ```bash
   cd ~/Downloads/route53-updater-main
   ```

### Step 2: Get Your AWS Information

#### 2a. Get Your Hosted Zone ID

1. Log into the [AWS Console](https://console.aws.amazon.com)
2. Go to **Services** → **Route 53**
3. Click **Hosted zones** in the left sidebar
4. Click on your domain name (e.g., `example.com`)
5. Copy the **Hosted zone ID** at the top right (looks like `Z1234567890ABC`)

#### 2b. Create AWS Access Keys

1. In AWS Console, go to **Services** → **IAM**
2. Click **Users** in the left sidebar
3. Click your username (or create a new user for this app)
4. Click the **Security credentials** tab
5. Scroll to **Access keys** section
6. Click **Create access key**
7. Choose **Application running outside AWS**
8. Click **Next**, then **Create access key**
9. **IMPORTANT:** Copy both:
   - Access key ID (looks like `AKIAIOSFODNN7EXAMPLE`)
   - Secret access key (looks like `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`)
   - You can only see the secret once, so save it now!

#### 2c. Set Up IAM Permissions

Your AWS user needs permission to update Route 53 records:

1. In IAM, click **Users** → your username
2. Click **Add permissions** → **Attach policies directly**
3. Click **Create policy**
4. Click the **JSON** tab
5. Paste this policy (replace `YOUR_HOSTED_ZONE_ID` with your actual ID from step 2a):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "route53:ListResourceRecordSets",
        "route53:ChangeResourceRecordSets"
      ],
      "Resource": "arn:aws:route53:::hostedzone/YOUR_HOSTED_ZONE_ID"
    }
  ]
}
```

6. Click **Next**
7. Name it `Route53-DNS-Updater-Policy`
8. Click **Create policy**
9. Go back to your user and attach this new policy

### Step 3: Create Your Configuration File

1. Make sure you're in the `route53-updater` folder:
   ```bash
   pwd
   # Should show: /path/to/route53-updater
   ```

2. Copy the example file:
   ```bash
   cp .env.example .env
   ```

3. Edit the `.env` file:
   ```bash
   nano .env
   ```
   (Or use any text editor: `vim`, `code`, `TextEdit`, etc.)

4. Fill in your information:
   ```
   # AWS Credentials (from Step 2b)
   AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
   AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

   # Route 53 Configuration (from Step 2a)
   HOSTED_ZONE_ID=Z1234567890ABC
   RECORD_NAME=home.example.com
   ```

5. Replace:
   - `AKIAIOSFODNN7EXAMPLE` with your actual Access Key ID
   - `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` with your actual Secret Access Key
   - `Z1234567890ABC` with your actual Hosted Zone ID
   - `home.example.com` with the subdomain you want to update

6. Save and exit (in nano: `Ctrl+O`, `Enter`, `Ctrl+X`)

### Step 4: Customize Settings (Optional)

You have two deployment options:

#### Option A: Standalone Deployment (Single App)

If you're running this as a standalone application, edit `docker-compose.yml`:

```bash
nano docker-compose.yml
```

Find the `environment:` section and modify:

```yaml
environment:
  # ... (AWS credentials loaded from .env file)
  
  # Update Settings - CHANGE THESE IF NEEDED:
  UPDATE_IPV4: "true"        # Set to "false" to disable IPv4 updates
  UPDATE_IPV6: "false"       # Set to "true" to enable IPv6 updates
  CHECK_INTERVAL: "300"      # Seconds between checks (300 = 5 minutes)
  TTL: "300"                 # DNS record TTL in seconds
  AWS_REGION: us-east-1      # Change if your Route 53 is in another region
```

Common changes:
- **Enable IPv6**: Change `UPDATE_IPV6: "false"` to `UPDATE_IPV6: "true"`
- **Check more often**: Change `CHECK_INTERVAL: "300"` to `"60"` (1 minute)
- **Check less often**: Change `CHECK_INTERVAL: "300"` to `"900"` (15 minutes)

#### Option B: Centralized Deployment (Multiple Apps)

If you manage multiple Docker apps from a central `compose.yaml` file, add this service definition:

```yaml
services:
  route53-updater:
    build: ./route53-updater
    container_name: route53-updater
    restart: unless-stopped
    env_file:
      - ./route53-updater/.env  # Points to the .env file in the subdirectory
    environment:
      AWS_REGION: us-east-1
      UPDATE_IPV4: "true"
      UPDATE_IPV6: "false"
      CHECK_INTERVAL: "300"
      TTL: "300"
```

Make sure your `.env` file is in the `route53-updater` subdirectory with your AWS credentials.

### Step 5: Start the Application

#### For Standalone Deployment:

1. Build and start the container:
   ```bash
   docker compose up -d
   ```

   You should see:
   ```
   Creating network "route53-updater_default" with the default driver
   Building route53-updater
   ...
   Creating route53-updater ... done
   ```

2. Check if it's running:
   ```bash
   docker compose ps
   ```

   Should show:
   ```
   NAME                STATE     PORTS
   route53-updater     Up        
   ```

3. View the logs to confirm it's working:
   ```bash
   docker compose logs -f
   ```

   You should see:
   ```
   Starting Route 53 DNS Updater
   Record: home.example.com
   Hosted Zone: Z1234567890ABC
   Check interval: 300 seconds
   IPv4 updates: enabled
   IPv6 updates: disabled
   --------------------------------------------------
     Fetched ipv4 from checkip.amazonaws.com: 203.0.113.45
     Fetched ipv4 from ipv4.icanhazip.com: 203.0.113.45
   ✓ ipv4 validated: 203.0.113.45 (both sources agree)
   ✓ Updated A record home.example.com to 203.0.113.45
   Next check in 300 seconds...
   ```

4. Press `Ctrl+C` to exit the logs (the container keeps running)

#### For Centralized Deployment:

1. From your main Docker apps directory, rebuild and restart all services:
   ```bash
   docker compose up -d --build
   ```

   Or to start only the route53-updater service:
   ```bash
   docker compose up -d route53-updater
   ```

2. View logs for this specific service:
   ```bash
   docker compose logs -f route53-updater
   ```

3. Press `Ctrl+C` to exit the logs (the container keeps running)

---

## Daily Usage

The container runs automatically in the background. You don't need to do anything!

### Useful Commands

```bash
# View live logs
docker compose logs -f

# Stop the updater
docker compose down

# Start it again
docker compose up -d

# Restart after changing settings
docker compose up -d --force-recreate

# Check if it's running
docker compose ps
```

### After Reboot

The container will automatically restart unless you run `docker compose down`. If you want it to start on boot, it's already configured with `restart: unless-stopped`.

---

## Troubleshooting

### "ERROR: HOSTED_ZONE_ID and RECORD_NAME must be set"
- Check your `.env` file exists and has the correct values
- Make sure there are no spaces around the `=` sign

### "Error updating DNS record: AccessDenied"
- Your IAM user doesn't have the right permissions
- Go back to Step 2c and verify the policy is attached

### "Could not fetch ipv4 from enough sources"
- Check your internet connection
- Verify Docker can access external websites

### "ERROR: ipv4 mismatch detected!"
- The two IP check services returned different IPs
- This is a safety feature - wait a few minutes and check again
- Could indicate network issues or DNS problems

### Container keeps restarting
```bash
docker compose logs
```
Look for error messages at the top of the output.

---

## Security Notes

- Your `.env` file contains sensitive credentials - never commit it to git
- The app validates IPs from two independent sources before updating
- Rate limiting prevents API abuse (max 1 update per 30 seconds per record)
- All inputs are validated and sanitized

---

## Uninstalling

```bash
# Stop and remove the container
docker compose down

# Remove the Docker image
docker rmi route53-updater_route53-updater

# Delete the folder
cd ..
rm -rf route53-updater
```
