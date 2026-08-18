Set WshShell = CreateObject("WScript.Shell")
' Replace the path below with the actual location of your .bat file
WshShell.Run chr(34) & "C:\Investment\start_stock_alert.bat" & Chr(34), 0
Set WshShell = Nothing