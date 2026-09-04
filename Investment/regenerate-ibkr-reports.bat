@echo off
setlocal EnableExtensions
REM Regenerate all IBKR Excel reports into C:\Investment\reports\
REM Usage:
REM   regenerate-ibkr-reports.bat
REM   regenerate-ibkr-reports.bat --offline

set "OFFLINE="
if /I "%~1"=="--offline" set "OFFLINE=1"

set "REPORTS=C:\Investment\reports"
if not exist "%REPORTS%" mkdir "%REPORTS%"

echo === 1/4 AccountStatement P1 ===
cd /d C:\Investment\IBKR-Download
python -m ibkr_download_reports --out "%REPORTS%\IBKR_AccountStatement_P1.xlsx"
if errorlevel 1 goto :fail

echo === 2/4 Buy/Sell (Flex + Activity) ===
cd /d C:\Investment\IBKR-Flex-BuySell
if defined OFFLINE (
  python flex_buysell_report.py --from-downloads --fill-missing-from-activity --discover --no-market-prices --output "%REPORTS%\IBKR_BuySell_Since_2020.xlsx"
) else (
  python flex_buysell_report.py --from-downloads --fill-missing-from-activity --discover --output "%REPORTS%\IBKR_BuySell_Since_2020.xlsx"
)
if errorlevel 1 goto :fail

echo === 3/4 Trade history (offline refresh) ===
python -m trade_history refresh --offline --no-market-prices
if errorlevel 1 (
  echo Refresh failed — trying force rebaseline...
  python -m trade_history baseline --force-rebaseline --offline --no-market-prices
  if errorlevel 1 goto :fail
)

echo === 4/4 FIFO batch P&L ===
cd /d C:\Investment\IBKR-BatchPnL
python batch_pnl_report.py --no-market-prices --output "%REPORTS%\IBKR_Batch_PnL.xlsx"
if errorlevel 1 goto :fail

echo.
echo Done. Open: %REPORTS%
dir /b "%REPORTS%\*.xlsx"
exit /b 0

:fail
echo ERROR: regenerate failed.
exit /b 1
