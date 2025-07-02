# Python
Offline Deployment Guide: Node.js + Express + Python on Linux (No Internet Access)

Overview:
- Target Environment: Linux (offline)
- Development Environment: Windows (online)
- Components:
  - Node.js + Express app
  - Python scripts with external modules
  - Offline installation of Node and Python dependencies

Step-by-Step Guide:

1. Prepare the Linux Machine
- Ensure the Linux machine has:
  - Compatible versions of Node.js and Python installed (offline via binaries)
  - Basic tools: tar, unzip, pip, npm, etc.

2. On Windows: Prepare Node.js Dependencies
- Install Node.js and your project:
  npm install
- Package all dependencies:
  npm ci --ignore-scripts
- Create a tarball of node_modules:
  tar -czf node_modules.tar.gz node_modules
- Copy your entire Node.js project (including package.json, package-lock.json, and node_modules.tar.gz) to a USB or shared drive.

3. On Windows: Prepare Python Dependencies
- Create a virtual environment:
  python -m venv venv
  venv\Scripts\activate
- Install required packages:
  pip install -r requirements.txt
- Download wheels for offline install:
  pip download -r requirements.txt -d offline_packages
- Zip the offline_packages folder and your Python scripts.

4. Transfer Files to Linux Machine
- Copy the following to the Linux machine:
  - Node.js project folder
  - node_modules.tar.gz
  - Python project folder
  - offline_packages folder
  - requirements.txt

5. On Linux: Set Up Node.js Environment
- Extract node modules:
  tar -xzf node_modules.tar.gz
- Verify Node.js and npm are installed:
  node -v
  npm -v

6. On Linux: Set Up Python Environment
- Create a virtual environment:
  python3 -m venv venv
  source venv/bin/activate
- Install packages from offline folder:
  pip install --no-index --find-links=offline_packages -r requirements.txt

7. Run the Application
- Start the Node.js server:
  node app.js
- Ensure Python scripts are executable and callable from Node.js

Optional Enhancements:
- Use pm2 for managing Node.js processes (can be installed offline)
- Use supervisor or systemd to keep services running
- Log outputs to files for debugging
