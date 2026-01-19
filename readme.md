# Caleb Discord Bot v2

A Discord bot with Role Assignment, Drink Counter, and Music Player features.

## Features
- 🎭 **Role Assignment** - React to emojis to get roles
- 🍻 **Drink Counter** - Track who owes drinks (per-channel)
- 🎵 **Music Player** - YouTube music with queue

---

## 🖥️ Local Development

### Run Locally (Windows PowerShell)
```powershell
cd "D:\Using\leisure\discordbot\Discord Bot"
.\.venv\Scripts\Activate.ps1
$env:DISCORD_TOKEN = "YOUR_TOKEN_HERE"
python calebv2.py
```

### Push Changes to GitHub
```powershell
git add .
git commit -m "your message here"
git push
```

---

## ☁️ AWS Server Commands

### Connect to Server

**Option A: AWS Web Console (Easier)**
1. Go to AWS → EC2 → Instances
2. Select your instance → Click **Connect**
3. Choose **EC2 Instance Connect** → Click **Connect**

**Option B: SSH from PowerShell**
```powershell
cd Downloads
ssh -i "discord-bot-key.pem" ubuntu@YOUR_PUBLIC_IP
```

---

### 🔄 Update Bot Code (Most Common!)
```bash
cd ~/caleb-discord-bot
git pull
sudo systemctl restart discordbot
```

### 📊 Check Bot Status
```bash
sudo systemctl status discordbot
```

### 📜 View Logs (Live)
```bash
sudo journalctl -u discordbot -f
```
Press `Ctrl+C` to exit logs.

### 🔁 Restart Bot
```bash
sudo systemctl restart discordbot
```

### 🛑 Stop Bot
```bash
sudo systemctl stop discordbot
```

### ▶️ Start Bot
```bash
sudo systemctl start discordbot
```

---

## 🆕 Fresh Server Setup (Only for New Server)

### 1. Install Dependencies
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv ffmpeg git -y
```

### 2. Clone Repository
```bash
git clone https://github.com/shl0402/caleb-discord-bot.git
cd caleb-discord-bot
```

### 3. Setup Python Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Create Service File
```bash
sudo nano /etc/systemd/system/discordbot.service
```

Paste this content:
```ini
[Unit]
Description=Discord Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/caleb-discord-bot
Environment="DISCORD_TOKEN=YOUR_TOKEN_HERE"
ExecStart=/home/ubuntu/caleb-discord-bot/venv/bin/python calebv2.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Save: `Ctrl+X` → `Y` → `Enter`

### 5. Enable and Start
```bash
sudo systemctl daemon-reload
sudo systemctl enable discordbot
sudo systemctl start discordbot
```

---

## 🔑 Change Discord Token

If you need to change the token:

```bash
sudo nano /etc/systemd/system/discordbot.service
```
Edit the `Environment="DISCORD_TOKEN=..."` line, save, then:
```bash
sudo systemctl daemon-reload
sudo systemctl restart discordbot
```

---

## 📝 Quick Reference

| Task | Command |
|------|---------|
| Update code | `cd ~/caleb-discord-bot && git pull && sudo systemctl restart discordbot` |
| Check status | `sudo systemctl status discordbot` |
| View logs | `sudo journalctl -u discordbot -f` |
| Restart | `sudo systemctl restart discordbot` |
| Stop | `sudo systemctl stop discordbot` |

---

## ⚠️ Important Notes

1. **Never commit your token to GitHub!** Use environment variables.
2. **Regenerate token** if it's ever exposed publicly.
3. **AWS Free Tier** is free for 12 months (t2.micro instance).
4. Bot auto-restarts on crash and server reboot.
