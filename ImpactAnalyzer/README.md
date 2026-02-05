# ImpactAnalyzer

A Python utility to capture artifacts for debugging banking applications.
It collects:
1.  **Server Logs** (via SSH)
2.  **Database Changes** (via Oracle DB Query)
3.  **Browser Console Logs** (via Chrome DevTools Protocol)

## 1. Setup & Installation

### Prerequisites
*   Python 3.8+ installed on your Windows Client.
*   Access to the Unix Server and Oracle Database.

### Install Dependencies
Run this command to downlaod and install the required Python packages:

```powershell
pip install -r requirements.txt
```

*(This installs `paramiko` for SSH, `oracledb` for Database, and `websocket-client` for Chrome).*

## 2. Configuration (`config.json`)

Edit `config.json` with your environment details.

### Server (Unix) - Password or Key
You can use either **Password** OR **SSH Key**.

```json
"server": {
    "host": "unix-prod-01",
    "user": "jboss",
    "password": "my_secret_password",  <-- Option A: Use Password
    "ssh_key_path": "",                <-- Option B: Leave empty if using password
    "log_path": "/app/jboss/standalone/log/server.log"
}
```

### Database (Oracle) - Password
Oracle DB connection requires a password (or Wallet).

```json
"database": {
    "user": "app_user",
    "password": "db_password"
}
```

## 3. Usage

1.  **Start your Test Preparation** (Open the banking app in Chrome with debugging enabled).
    *   *Note*: Start Chrome with: `chrome.exe --remote-debugging-port=9222`
2.  **Run the Analyzer**:
    Select the **Market** (e.g., SG, MY) and **App Type** (customer, admin).
    
    ```powershell
    # Run for 15 minutes for SG Customer App
    python main.py --market SG --app customer --duration 15
    
    # Run for MY Bank Admin App
    python main.py --market MY --app admin --duration 10
    ```
3.  **Perform Test**: Do your manual testing in the next X minutes.
4.  **Result**: A zip file (e.g., `reports/analysis_SG_customer_20260205.zip`) will be created.

---

## Appendix: SSH Key Generation (If avoiding passwords)

If you prefer **SSH Keys** (more secure, no hardcoded passwords), follow these instructions:

### Step 1: Generate Key Pair (On Windows)
Open PowerShell and run:
```powershell
ssh-keygen -t rsa -b 4096 -f C:\Users\YourUser\.ssh\id_rsa
```
*   Press Enter for no passphrase (or set one if required).
*   This creates two files:
    *   `id_rsa` (Private Key - Keep secret)
    *   `id_rsa.pub` (Public Key - Share with server)

### Step 2: Import Key to Unix Server
You need to add the content of `id_rsa.pub` to the server's `authorized_keys` file.

**Option A: Manual**
1.  Open `id_rsa.pub` in Notepad and copy the content.
2.  SSH into the Unix server using your password.
3.  Edit `~/.ssh/authorized_keys`:
    ```bash
    mkdir -p ~/.ssh
    nano ~/.ssh/authorized_keys
    # Paste the content on a new line
    chmod 700 ~/.ssh
    chmod 600 ~/.ssh/authorized_keys
    ```

**Option B: Automated (if you have `ssh-copy-id`)**
```bash
ssh-copy-id jboss@unix-prod-01
```

### Step 3: Update `config.json`
Set the path in the config:
```json
"ssh_key_path": "C:/Users/YourUser/.ssh/id_rsa"
```
