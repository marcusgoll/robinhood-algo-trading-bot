# Dokploy SSH Setup Guide

**Date**: 2025-10-27
**Purpose**: Configure SSH access and deployment keys for Dokploy
**Status**: Configured

---

## Summary

✅ **SSH Key Saved**: `~/.ssh/dokploy`
✅ **Hetzner VPS IP**: `178.156.129.179`
✅ **Dokploy Dashboard**: `http://178.156.129.179:9100`
✅ **SSH Port**: 22 (standard)

---

## Accessing Your Dokploy Dashboard

### Via Browser (Dashboard)

1. **Open browser**:
   ```
   http://178.156.129.179:9100
   ```

2. **Login** with your Dokploy credentials

3. **Navigate to Settings → SSH Keys**

---

## Setting Up Dokploy SSH Key for Git Deployments

The Dokploy SSH key you provided is used for **Git repository authentication**. This allows Dokploy to automatically pull code from your GitHub repository during deployments.

### Step 1: Add SSH Key to Dokploy Dashboard

1. **Login to Dokploy** at `http://178.156.129.179:9100`

2. **Go to Settings**:
   - Click user icon (top right)
   - Select "Settings" or "Admin Settings"

3. **Navigate to SSH Keys** (might be under):
   - Settings → SSH Keys
   - Or: Admin → SSH Keys

4. **Add New SSH Key**:
   - Click "Add SSH Key" or "New Key"
   - Name: `dokploy-deploy`
   - Key type: `public`
   - Paste public key:
   ```
   ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCxi7MpYWs5D5Q9MwBNfpHHwTiPd7LogH5oHJZLRE45GgpNkw4Ojo8pAfsG0z1sYx/IKzpBq6LEqL+OMSZ3diN4hY+itR3/miPS0IS8NLecUpqO0b2Yezyu+D76+TDfgeq6yFYBLMsAIQGc/zoIAEscvgOxl58trO/slaEGPuC4kdYfJ4jsSiUlNZtWnD0JEBmTdTZF5d3U4EAw3YKjPNqvvXUrVZ+Frpv7wJ98nnOmvVL0mMI+KhKlYf2je/4gkPcP6B12Dd39XAbW4OAZuhZ6IQ6wOljAr3jmT1RmMssOBCyhZVHf0KyuCoU1E6F31HOOtXfYFXe0A4o9DMDKGUY9aKM8h7ibLp6PbAWZPYj7/VfmzhcWt4nuwB/mpo5NNmvdRUqXikFvbHh75DhYjouAOmH3RmTv7KjL6NyekqD/Q5kq3PYs5SJoYUNZ8f6cTrF2Taz9B8qLGAuRdRgLUT9/aeMqSWIZqoeGN45U5Gk0DAxjy3S1YATYccAX5ZMAl/S4Rs5ci6/NezcgxjsrGi/ZcQ8C9rY3l03dE5mris6YMClLafLyw2IyKffBuMMX1TePu288+JeXS2lpnn+zJX0AXsSczHkispjhKpRJg8gwmnb1JEFYWrnfvoTGs4JKbVah6oNw0AzogqVRigKDm14noq9FX4BrwhjliSXbwVVwJw== dokploy
   ```

5. **Save Key**

### Step 2: Configure GitHub Repository Access

1. **In Dokploy Dashboard**, when creating a deployment:
   - Select "GitHub" as source
   - Choose your repository: `robinhood-algo-trading-bot`
   - Branch: `main`

2. **Dokploy will use the SSH key** to authenticate with GitHub

3. **If deployment fails due to SSH**:
   - Go to GitHub repository → Settings → Deploy Keys
   - Add the public key above with "Allow write access"

---

## SSH Access for VPS Management

### Direct VPS Access

You already have access via:

```bash
ssh hetzner
```

This connects to the Hetzner VPS at `178.156.129.179` as the `root` user.

### Common Commands

```bash
# Check Dokploy status
ssh hetzner "docker ps | grep dokploy"

# View Dokploy logs
ssh hetzner "docker logs dokploy -f"

# Check Dokploy dashboard API
ssh hetzner "curl http://localhost:9100/api/health"

# View trading bot containers
ssh hetzner "docker ps | grep trading"

# SSH into the VPS for maintenance
ssh hetzner
```

---

## Local SSH Configuration

Your local `~/.ssh/config` is configured as:

```
Host hetzner
    HostName 178.156.129.179
    User root
    IdentityFile ~/.ssh/id_rsa

Host dokploy-deploy
    HostName 178.156.129.179
    User dokploy
    IdentityFile ~/.ssh/dokploy
    StrictHostKeyChecking accept-new
```

### Usage

```bash
# Access VPS as root
ssh hetzner

# Use dokploy deployment key (internal to Dokploy)
ssh dokploy-deploy  # For debugging deployments
```

---

## SSH Key Locations

Local machine:
```
~/.ssh/dokploy          # Dokploy private key (600 perms)
~/.ssh/id_rsa           # Default SSH key for Hetzner
~/.ssh/config           # SSH configuration
~/.ssh/known_hosts      # Known hosts fingerprints
```

---

## Testing SSH Connection

### Test Hetzner Access

```bash
ssh hetzner "echo 'Connection successful!' && hostname"
```

Expected output:
```
Connection successful!
cfipros-prod-app-01
```

### Test Dokploy Access

```bash
ssh hetzner "docker exec dokploy whoami"
```

---

## Security Notes

✅ **Private Key Secured**:
- File permissions: `600` (read/write owner only)
- Location: `~/.ssh/dokploy`
- Never commit to Git

✅ **Best Practices**:
- Keep private key safe
- Use SSH agent for convenience (optional)
- Rotate keys periodically
- Use different keys for different services

---

## Next Steps: Using Dokploy SSH in Your LLM

When your LLM needs to manage Dokploy:

1. **SSH to Hetzner VPS**:
   ```bash
   ssh hetzner "command-here"
   ```

2. **Example: Check Dokploy Status**:
   ```bash
   ssh hetzner "docker ps | grep -i dokploy"
   ```

3. **Example: View Deployment Logs**:
   ```bash
   ssh hetzner "docker logs trading-bot-prod -f"
   ```

4. **Example: Manage Services**:
   ```bash
   ssh hetzner "docker-compose -f /path/to/compose.yml up -d"
   ```

---

## Dokploy Dashboard Access

**Direct URL**: `http://178.156.129.179:9100`

**Services Running**:
- ✅ Dokploy: Port 9100 (web dashboard)
- ✅ PostgreSQL: Port 5432 (internal)
- ✅ Redis: Port 6379 (internal)

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **Cannot SSH to hetzner** | Check IP firewall rules: `ssh hetzner "sudo ufw status"` |
| **Dokploy dashboard not accessible** | Check if container is running: `ssh hetzner "docker ps \| grep dokploy"` |
| **SSH key permission denied** | Fix permissions: `chmod 600 ~/.ssh/dokploy` |
| **Dokploy deployments failing** | Verify SSH key is added to GitHub repo deploy keys |
| **Cannot access from LLM** | Ensure SSH key is in `~/.ssh/dokploy` and config is correct |

---

**Status**: ✅ SSH Access Configured
**Last Updated**: 2025-10-27
