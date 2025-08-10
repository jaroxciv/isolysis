# run_dev.ps1 - Isolysis Development Environment

# Colors for output
$Green = "`e[32m"
$Yellow = "`e[33m"
$Red = "`e[31m"
$Reset = "`e[0m"

Write-Host "${Green}🚀 Starting Isolysis Development Environment${Reset}"

# Check if .venv exists
if (-not (Test-Path ".venv")) {
    Write-Host "${Red}❌ No .venv directory found. Please create virtual environment first.${Reset}"
    exit 1
}

# Activate virtual environment
Write-Host "${Yellow}📦 Activating virtual environment...${Reset}"
if (Test-Path ".venv\Scripts\Activate.ps1") {
    & ".venv\Scripts\Activate.ps1"
} else {
    Write-Host "${Red}❌ Could not find virtual environment activation script${Reset}"
    exit 1
}

# Global variable to track API process
$script:ApiProcess = $null

# Function to cleanup background processes
function Cleanup {
    Write-Host "`n${Yellow}🛑 Shutting down services...${Reset}"
    if ($script:ApiProcess -and !$script:ApiProcess.HasExited) {
        $script:ApiProcess.Kill()
        Write-Host "${Green}✅ API server stopped${Reset}"
    }
    exit 0
}

# Set trap to cleanup on script exit
$null = Register-EngineEvent PowerShell.Exiting -Action { Cleanup }

try {
    # Start API server in background
    Write-Host "${Yellow}🔧 Starting API server...${Reset}"
    $script:ApiProcess = Start-Process -FilePath "uv" -ArgumentList "run", "uvicorn", "api.app:app", "--reload", "--port", "8000" -PassThru -NoNewWindow

    # Wait for API to start
    Write-Host "${Yellow}⏳ Waiting for API server to start...${Reset}"
    Start-Sleep -Seconds 3

    # Check if API is running
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Host "${Green}✅ API server running on http://localhost:8000${Reset}"
            Write-Host "${Green}📖 API docs available at http://localhost:8000/docs${Reset}"
        }
    }
    catch {
        Write-Host "${Red}❌ API server failed to start or health check failed${Reset}"
        Cleanup
    }

    # Start Streamlit app
    Write-Host "${Yellow}🎨 Starting Streamlit app...${Reset}"
    Write-Host "${Green}🌐 Streamlit will open at http://localhost:8501${Reset}"
    Write-Host "${Yellow}Press Ctrl+C to stop both services${Reset}"

    # This will block until Streamlit is stopped
    uv run streamlit run st_app.py

}
catch {
    Write-Host "${Red}❌ Error occurred: $_${Reset}"
}
finally {
    Cleanup
}