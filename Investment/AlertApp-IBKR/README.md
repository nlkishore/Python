# AlertApp-IBKR — ARCHIVED (2026-08-19)

This folder's scripts have been **consolidated into `AlertApp\backgroundAlert1.py`**.

## What was merged

| Feature | Origin | Now in |
|---------|--------|--------|
| Price threshold monitor | `AlertApp\backgroundAlert1.py` (old) | `AlertApp\backgroundAlert1.py` |
| `STATUS` command | both | `AlertApp\backgroundAlert1.py` |
| `SUPPORT SYMBOL` command | `AlertApp-IBKR\backgroundAlert.py` | `AlertApp\backgroundAlert1.py` |
| `SOLD` / `SEND` command | `AlertApp-IBKR\backgroundAlert.py` | `AlertApp\backgroundAlert1.py` |
| `WATCHLIST` command | new | `AlertApp\backgroundAlert1.py` |
| Single-instance mutex | `AlertApp-IBKR\backgroundAlert.py` | `AlertApp\backgroundAlert1.py` |
| Heartbeat / dead-man's switch | `AlertApp-IBKR\backgroundAlert.py` | `AlertApp\backgroundAlert1.py` |
| Watchdog (auto-restart) | `AlertApp-IBKR\watchdog.py` | `AlertApp\watchdog.py` |
| Task Scheduler install bat | `AlertApp-IBKR\install-scheduled-tasks.bat` | `AlertApp\install-scheduled-tasks.bat` |

## How to use the consolidated app

```
cd C:\Investment\AlertApp
python backgroundAlert1.py          # manual / foreground run
run-green-api-listener.bat          # same, via bat shortcut
install-scheduled-tasks.bat         # auto-start on reboot + watchdog
```

Root launchers still work:
```
C:\Investment\start_stock_alert.bat   # start
C:\Investment\stop_stock_alert.bat    # stop
```

## Archived scripts

The original scripts are kept in `archive\` for reference only. Do not run them —
they share the same Green API instance and would cause a 502 RMQ_ERROR race condition.
