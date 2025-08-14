<#
.SYNOPSIS
    Downloads and updates the ssm-manager application from its latest GitHub release.

.DESCRIPTION
    This script performs the following actions:
    1.  Finds the latest release for the ssm-manager GitHub repository.
    2.  Downloads the latest version's zip file.
    3.  Creates a destination directory if it doesn't exist.
    4.  Backs up the 'preferences.json' file if it exists.
    5.  Deletes the existing ssm_manager application folder.
    6.  Extracts the new application files from the downloaded zip.
    7.  Restores the backed-up 'preferences.json' file.
    8.  Cleans up temporary files.

.NOTES
    This script requires an internet connection and is designed for a specific GitHub repository
    and file structure. It should be run with administrative privileges if the target
    directories require them.
#>

# ==============================================================================
# Define Parameters
# ==============================================================================
[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$destinationBaseDir = "C:\Program Files (x86)"
)

# ==============================================================================
# Define Variables
# ==============================================================================
$gitHubRepo = "napalm255/ssm-manager"
$appDir = "$destinationBaseDir\ssm_manager"
$preferencesFile = "$appDir\preferences.json"
$tempDir = "$env:TEMP\ssm_manager_update"
$backupPreferencesPath = "$tempDir\preferences.json.bak"

# ==============================================================================
# Get the latest release information
# ==============================================================================
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

# ==============================================================================
# Create necessary directories
# ==============================================================================
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

# ==============================================================================
# Backup the 'preferences.json' file if it exists
# ==============================================================================
if (Test-Path $preferencesFile) {
    Write-Host "Backing up preferences.json..." -ForegroundColor Cyan
    try {
        Copy-Item -Path $preferencesFile -Destination $backupPreferencesPath -Force -ErrorAction Stop
        Write-Host "preferences.json backed up to $backupPreferencesPath" -ForegroundColor Green
    } catch {
        Write-Host "Failed to back up preferences.json. Aborting update." -ForegroundColor Red
        exit
    }
}
else {
    Write-Host "preferences.json not found. No backup needed." -ForegroundColor Cyan
}

# ==============================================================================
# Delete the old application folder
# ==============================================================================
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

# ==============================================================================
# Download the latest release
# ==============================================================================
try {
    Write-Host "Downloading new release..." -ForegroundColor Cyan
    Invoke-WebRequest -Uri $zipDownloadUrl -OutFile $zipFilePath -ErrorAction Stop
    Write-Host "Download complete." -ForegroundColor Green
} catch {
    Write-Host "Failed to download the release." -ForegroundColor Red
    exit 1
}

# ==============================================================================
# Extract the downloaded zip file
# ==============================================================================

try {
    Write-Host "Extracting files to $destinationBaseDir..." -ForegroundColor Cyan
    Expand-Archive -Path $zipFilePath -DestinationPath $destinationBaseDir -Force -ErrorAction Stop
    Write-Host "Extraction complete." -ForegroundColor Green
} catch {
    Write-Host "An error occurred during download or extraction. Aborting." -ForegroundColor Red
    exit 1
}

# ==============================================================================
# Restore 'preferences.json'
# ==============================================================================
if (Test-Path $backupPreferencesPath) {
    Write-Host "Restoring backed up preferences.json..." -ForegroundColor Green
    try {
        Copy-Item -Path $backupPreferencesPath -Destination $preferencesFile -Force -ErrorAction Stop
        Write-Host "preferences.json restored successfully."
    } catch {
        Write-Host "Failed to restore preferences.json. Please check the backup file." -ForegroundColor Red
    }
}

# ==============================================================================
# Create desktop shortcut
# ==============================================================================
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

# ==============================================================================
# Clean up and finish
# ==============================================================================
Write-Host "Cleaning up temporary files..." -ForegroundColor Cyan
Remove-Item -Path $tempDir -Recurse -Force
Write-Host "Update finished successfully!" -ForegroundColor Green
