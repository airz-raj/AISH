@echo off
echo === System Information ===
systeminfo | findstr /B /C:"OS Name" /C:"OS Version"
echo.
echo === IP Configuration ===
ipconfig | findstr "IPv4"
echo.
pause