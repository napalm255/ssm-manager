# Check if pyinstaller is installed
if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Host "PyInstaller is not installed." -ForegroundColor Red
    Write-Host "You may want to activate your virtual environment." -ForegroundColor Yellow
    exit 1
}

# Remove cache, log, and preferences files
Remove-Item -Path "cache" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "app.log" -Force -ErrorAction SilentlyContinue
Remove-Item -Path "preferences.json" -Force -ErrorAction SilentlyContinue

# Navigate to the ssm-manager directory
cd ssm-manager

# Remove build, dist, __pycache__, and spec file
Remove-Item -Path "build" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "dist" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "__pycache__" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "ssm-manager.spec" -Force -ErrorAction SilentlyContinue

# Run PyInstaller
pyinstaller --onedir --noconsole --clean --noconfirm `
    --add-data "static:static" `
    --add-data "templates:templates" `
    --icon="static/favicon.ico" `
    --name="ssm-manager" `
    app.py

# Create a zip file of the contents of dist/SSM-Manager
# if (Test-Path -Path "dist\ssm-manager") {
#     Compress-Archive -Path "dist\ssm-manager\*" -DestinationPath "dist\ssm-manager.zip" -Force
# } else {
#     Write-Warning "Directory 'dist\ssm-manager' not found. Skipping zip creation."
# }

# Navigate back to the parent directory (optional)
cd ..
