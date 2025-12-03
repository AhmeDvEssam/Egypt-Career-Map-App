$pythonPath = "d:\Hire Q Project\Modeling _2\DashApp.py"

# Kill existing processes
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force

# Wait
Start-Sleep -Seconds 3

# Start server
Write-Host "🚀 Starting Dash App..." -ForegroundColor Green
python.exe $pythonPath
