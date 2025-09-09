<#
.SYNOPSIS
    Downloads and updates the ssm-manager application from its latest GitHub release.

.DESCRIPTION
    This script performs the following actions:
    1.  Finds the latest release for the ssm-manager GitHub repository.
    2.  Downloads the latest version's zip file.
    3.  Creates a destination directory if it doesn't exist.
    4.  Deletes the existing ssm_manager application folder.
    5.  Extracts the new application files from the downloaded zip.
    6.  Cleans up temporary files.

.NOTES
    This script requires an internet connection and is designed for a specific GitHub repository
    and file structure. It should be run with administrative privileges if the target
    directories require them.
#>

# =============================================================================
# Define Parameters
# =============================================================================
[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$destinationBaseDir = "C:\Program Files (x86)"
)

# =============================================================================
# Define Variables
# =============================================================================
$gitHubRepo = "napalm255/ssm-manager"
$appDir = "$destinationBaseDir\ssm_manager"
$tempDir = "$env:TEMP\ssm_manager_update"

# =============================================================================
# Check for administrative privileges
# =============================================================================
if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "This script must be run as an administrator. Please restart PowerShell with elevated privileges." -ForegroundColor Red
    exit 1
}

# =============================================================================
# Get the latest release information
# =============================================================================
Write-Host "Fetching latest release information from GitHub..." -ForegroundColor Cyan
try {
    # Use Invoke-RestMethod for easier JSON parsing from the GitHub API
    $releaseInfo = Invoke-RestMethod -Uri "https://api.github.com/repos/$gitHubRepo/releases/latest" -ErrorAction Stop

    # The API response contains the full download URL for the zip.
    # We look for an asset that is a zip file.
    $zipAsset = $releaseInfo.assets | Where-Object { $_.name -like "*.zip" }

    if ($null -eq $zipAsset) {
        throw "Could not find a zip file in the latest release assets."
    }

    $zipDownloadUrl = $zipAsset.browser_download_url
    $zipFileName = $zipAsset.name
    $zipFilePath = "$tempDir\$zipFileName"

    Write-Host "Found latest release: $($releaseInfo.tag_name)" -ForegroundColor Blue
    Write-Host "Download URL: $zipDownloadUrl" -ForegroundColor Blue
} catch {
    Write-Host "Error fetching release info. Please check the repository URL and your internet connection." -ForegroundColor Red
    exit
}

# =============================================================================
# Create necessary directories
# =============================================================================
# Ensure the temporary directory exists and is clean
if (Test-Path $tempDir) {
    Remove-Item $tempDir -Recurse -Force
}
New-Item -ItemType Directory -Path $tempDir | Out-Null

# Ensure the destination directory exists
if (-not (Test-Path $destinationBaseDir)) {
    Write-Host "Creating destination directory: $destinationBaseDir"
    New-Item -ItemType Directory -Path $destinationBaseDir | Out-Null
}

# =============================================================================
# Delete the old application folder
# =============================================================================
if (-not (Test-Path $appDir)) {
    Write-Host "No existing application folder found. Proceeding with update." -ForegroundColor Green
}
else {
    while (Test-Path $appDir) {
        Write-Host "Deleting existing application folder: $appDir" -ForegroundColor Yellow
        try {
            Remove-Item -Path $appDir -Recurse -Force -ErrorAction Stop
            Write-Host "Old application folder deleted successfully." -ForegroundColor Green
        } catch {
            Write-Host "Failed to delete the old application folder. Please close any running instances of the application and try again." -ForegroundColor Red
            Sleep -Seconds 5
        }
    }
}

# =============================================================================
# Download the latest release
# =============================================================================
try {
    Write-Host "Downloading new release..." -ForegroundColor Cyan
    Invoke-WebRequest -Uri $zipDownloadUrl -OutFile $zipFilePath -ErrorAction Stop
    Write-Host "Download complete." -ForegroundColor Green
} catch {
    Write-Host "Failed to download the release." -ForegroundColor Red
    exit 1
}

# =============================================================================
# Extract the downloaded zip file
# =============================================================================

try {
    Write-Host "Extracting files to $destinationBaseDir..." -ForegroundColor Cyan
    Expand-Archive -Path $zipFilePath -DestinationPath $destinationBaseDir -Force -ErrorAction Stop
    Write-Host "Extraction complete." -ForegroundColor Green
} catch {
    Write-Host "An error occurred during download or extraction. Aborting." -ForegroundColor Red
    exit 1
}

# =============================================================================
# Remove the compatibility setting to run as administrator
# =============================================================================
try {
    $exePath = "$appDir\ssm_manager.exe"
    Write-Host "Setting compatibility for $exePath to run as administrator..." -ForegroundColor Cyan
    Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers" -Name $exePath -ErrorAction SilentlyContinue
} catch {
    Write-Host "Failed to set compatibility settings. You may need to set this manually." -ForegroundColor Red
}

# =============================================================================
# Create desktop shortcut
# =============================================================================
try {
    Write-Host "Creating desktop shortcut..." -ForegroundColor Cyan
    $targetPath = "$appDir\ssm_manager.exe"
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut([Environment]::GetFolderPath('Desktop') + "\ssm_manager.lnk")
    $shortcut.TargetPath = $targetPath
    $shortcut.WorkingDirectory = "$destinationBaseDir\ssm_manager"
    $shortcut.WindowStyle = 1
    $shortcut.Description = "Shortcut to SSM Manager"
    $shortcut.IconLocation = "$targetPath, 0"
    $shortcut.Save()
    Write-Host "Desktop shortcut created successfully." -ForegroundColor Green
} catch {
    Write-Host "Failed to create desktop shortcut. You may need to create it manually." -ForegroundColor Red
}

# =============================================================================
# Clean up and finish
# =============================================================================
Write-Host "Cleaning up temporary files..." -ForegroundColor Cyan
Remove-Item -Path $tempDir -Recurse -Force
Write-Host "Update finished successfully!" -ForegroundColor Green
