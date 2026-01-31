# Git & GitHub Guide

## First Time Setup (One Time Only)

### 1. Configure Git Identity
```bash
git config --global user.name "Your Name"
git config --global user.email "your-email@example.com"
```

### 2. Generate an SSH Key Pair (Local Machine) (Recommended)
```bash
ssh-keygen -t ed25519 -C "your-email@example.com"
```
Press Enter for all prompts (default location, no passphrase).

### 3. Add SSH Key to GitHub
```bash
# Copy the key (Windows)
type %USERPROFILE%\.ssh\id_ed25519.pub

# Copy the key (Linux/Mac)
cat ~/.ssh/id_ed25519.pub
```
1. Go to GitHub → Settings → SSH and GPG keys
2. Click "New SSH key"
3. Paste the key and save

---

## Daily Git Commands

### Push Changes to GitHub
```bash
git add -A                          # Stage all changes
git commit -m "Your message here"   # Commit with message
git push                            # Push to GitHub
```

### Pull Latest Changes
```bash
git pull
```

### Check Status
```bash
git status                          # See what's changed
git log --oneline -5                # See recent commits
```

---

## AWS Server - Pull & Restart Bot

```bash
cd ~/caleb-discord-bot
git pull
sudo systemctl restart caleb-bot
```

### Check Bot Status
```bash
sudo systemctl status caleb-bot     # Check if running
sudo journalctl -u caleb-bot -f     # View live logs
```

---

## Clone Repository (New Machine)

```bash
git clone git@github.com:shl0402/caleb-discord-bot.git
cd caleb-discord-bot
```

---

## Common Issues

### "Permission denied (publickey)"
- SSH key not set up. Follow steps 2-3 above.

### "Please tell me who you are"
- Run the git config commands from step 1.

### "Failed to push"
- Run `git pull` first, then `git push` again.
