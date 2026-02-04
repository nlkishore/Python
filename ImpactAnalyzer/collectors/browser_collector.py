import websocket
import json
import requests
import threading
import time
import os

class BrowserCollector:
    def __init__(self, config):
        self.port = config.get('debug_port', 9222)
        self.logs = []
        self.running = False
        self.ws = None
        
    def start_capture(self):
        """Starts capturing logs in a background thread."""
        self.running = True
        self.logs = [] # Clear previous
        
        try:
            # 1. Get Web Socket URL
            url = f"http://localhost:{self.port}/json"
            resp = requests.get(url)
            tabs = resp.json()
            
            # Find a page that isn't an extension or empty
            target_tab = None
            for tab in tabs:
                if tab['type'] == 'page':
                    target_tab = tab
                    break
            
            if not target_tab:
                print("[-] No active Chrome page found on port 9222.")
                return

            ws_url = target_tab['webSocketDebuggerUrl']
            
            # 2. Connect
            self.ws = websocket.WebSocketApp(ws_url, 
                                             on_message=self._on_message,
                                             on_open=self._on_open,
                                             on_error=self._on_error)
            
            self.thread = threading.Thread(target=self.ws.run_forever)
            self.thread.daemon = True
            self.thread.start()
            print("[+] Browser Console Capture Started.")
            
        except Exception as e:
            print(f"[-] Error parsing browser: {e}. Is Chrome started with --remote-debugging-port={self.port}?")

    def stop_capture(self, output_dir):
        """Stops capture and saves to file."""
        self.running = False
        if self.ws:
            self.ws.close()
            
        filename = os.path.join(output_dir, "browser_console.log")
        with open(filename, "w", encoding="utf-8") as f:
            for log in self.logs:
                f.write(log + "\n")
        
        print(f"[+] Browser Logs saved to {filename} ({len(self.logs)} entries)")
        return filename

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            if "method" in data and data["method"] == "Runtime.consoleAPICalled":
                params = data["params"]
                log_type = params["type"]
                timestamp = params["timestamp"] # Epoch
                args = params["args"]
                content = " ".join([str(arg.get("value", arg.get("description", ""))) for arg in args])
                
                log_entry = f"[{log_type.upper()}] {content}"
                self.logs.append(log_entry)
        except:
            pass
            
    def _on_open(self, ws):
        ws.send(json.dumps({"id": 1, "method": "Runtime.enable"}))
        
    def _on_error(self, ws, error):
        pass # Handle errors silently in background
