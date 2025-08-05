@echo off
setlocal EnableDelayedExpansion

REM JARVIS-MK42 Windows Production Deployment Script
REM This script handles automated deployment with rollback capabilities

set "CONTAINER_NAME=jarvis-mk42-app"
set "IMAGE_NAME=jarvis-mk42:latest"
set "BACKUP_DIR=C:\jarvis\backups"
set "LOG_FILE=C:\logs\jarvis-deploy.log"

REM Create directories if they don't exist
if not exist "C:\logs" mkdir "C:\logs"
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

REM Logging function
:log
echo [%date% %time%] %~1 >> "%LOG_FILE%"
echo [%date% %time%] %~1
goto :eof

:error
echo [ERROR] %~1 >> "%LOG_FILE%"
echo [ERROR] %~1
exit /b 1

:success
echo [SUCCESS] %~1 >> "%LOG_FILE%"
echo [SUCCESS] %~1
goto :eof

:warning
echo [WARNING] %~1 >> "%LOG_FILE%"
echo [WARNING] %~1
goto :eof

REM Pre-deployment checks
:pre_deploy_checks
call :log "Starting pre-deployment checks..."

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    call :error "Docker is not running. Please start Docker and try again."
    goto :eof
)

REM Check if required files exist
if not exist "docker-compose.yml" (
    call :error "docker-compose.yml not found in current directory"
    goto :eof
)

if not exist ".env" (
    call :warning ".env file not found. Using .env.example as template..."
    copy ".env.example" ".env" >nul
    call :error "Please configure .env file with your settings and run again"
    goto :eof
)

call :success "Pre-deployment checks passed"
goto :eof

REM Create backup of current deployment
:create_backup
call :log "Creating backup of current deployment..."

set "BACKUP_TIMESTAMP=%date:~-4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "BACKUP_TIMESTAMP=%BACKUP_TIMESTAMP: =0%"
set "CURRENT_BACKUP_DIR=%BACKUP_DIR%\backup_%BACKUP_TIMESTAMP%"
mkdir "%CURRENT_BACKUP_DIR%" 2>nul

REM Backup database
docker ps | findstr "jarvis-postgres" >nul
if not errorlevel 1 (
    call :log "Backing up database..."
    docker exec jarvis-postgres pg_dump -U jarvis jarvis_db > "%CURRENT_BACKUP_DIR%\database_backup.sql"
)

REM Backup application data
if exist "data" (
    call :log "Backing up application data..."
    xcopy "data" "%CURRENT_BACKUP_DIR%\data\" /E /I /Q
)

REM Backup logs
if exist "logs" (
    call :log "Backing up logs..."
    xcopy "logs" "%CURRENT_BACKUP_DIR%\logs\" /E /I /Q
)

REM Save current image for rollback
docker images | findstr "%IMAGE_NAME%" >nul
if not errorlevel 1 (
    call :log "Saving current image for rollback..."
    docker save "%IMAGE_NAME%" | gzip > "%CURRENT_BACKUP_DIR%\current_image.tar.gz"
)

echo %CURRENT_BACKUP_DIR% > "%BACKUP_DIR%\latest_backup_path.txt"
call :success "Backup created at %CURRENT_BACKUP_DIR%"
goto :eof

REM Deploy new version
:deploy
call :log "Starting deployment..."

REM Build new image
call :log "Building new Docker image..."
docker-compose build --no-cache jarvis-app
if errorlevel 1 (
    call :error "Failed to build Docker image"
    goto :eof
)

REM Test the new image
call :log "Testing new image..."
docker-compose run --rm jarvis-app python -c "import app; print('Application imports successfully')"
if errorlevel 1 (
    call :error "New image failed testing"
    goto :eof
)

REM Stop current containers gracefully
call :log "Stopping current containers..."
docker-compose down --timeout 30

REM Start new containers
call :log "Starting new containers..."
docker-compose up -d
if errorlevel 1 (
    call :error "Failed to start new containers"
    goto :eof
)

REM Wait for services to be ready
call :log "Waiting for services to be ready..."
timeout /t 30 /nobreak >nul

REM Health check
set "max_attempts=10"
set "attempt=1"

:health_check_loop
call :log "Health check attempt %attempt%/%max_attempts%..."

curl -f http://localhost:8000/health >nul 2>&1
if not errorlevel 1 (
    call :success "Application is healthy!"
    goto :deploy_success
)

if %attempt% equ %max_attempts% (
    call :error "Health check failed after %max_attempts% attempts"
    goto :eof
)

timeout /t 10 /nobreak >nul
set /a attempt+=1
goto :health_check_loop

:deploy_success
call :success "Deployment completed successfully"
goto :eof

REM Rollback to previous version
:rollback
call :log "Starting rollback process..."

if not exist "%BACKUP_DIR%\latest_backup_path.txt" (
    call :error "No backup found for rollback"
    goto :eof
)

set /p ROLLBACK_DIR=<"%BACKUP_DIR%\latest_backup_path.txt"

if not exist "%ROLLBACK_DIR%" (
    call :error "Backup directory not found: %ROLLBACK_DIR%"
    goto :eof
)

REM Stop current containers
call :log "Stopping current containers..."
docker-compose down --timeout 30

REM Restore previous image
if exist "%ROLLBACK_DIR%\current_image.tar.gz" (
    call :log "Restoring previous image..."
    docker load < "%ROLLBACK_DIR%\current_image.tar.gz"
)

REM Restore database
if exist "%ROLLBACK_DIR%\database_backup.sql" (
    call :log "Restoring database..."
    docker-compose up -d postgres
    timeout /t 10 /nobreak >nul
    docker exec -i jarvis-postgres psql -U jarvis -d jarvis_db < "%ROLLBACK_DIR%\database_backup.sql"
)

REM Restore data
if exist "%ROLLBACK_DIR%\data" (
    call :log "Restoring application data..."
    if exist "data" rmdir /s /q "data"
    xcopy "%ROLLBACK_DIR%\data" "data\" /E /I /Q
)

REM Start containers
call :log "Starting containers..."
docker-compose up -d

call :success "Rollback completed successfully"
goto :eof

REM Main deployment process
set "command=%~1"
if "%command%"=="" set "command=deploy"

if "%command%"=="deploy" (
    call :log "Starting JARVIS-MK42 deployment process..."
    call :pre_deploy_checks
    call :create_backup
    call :deploy
    call :success "Deployment process completed!"
) else if "%command%"=="rollback" (
    call :log "Starting rollback process..."
    call :rollback
    call :success "Rollback process completed!"
) else if "%command%"=="backup" (
    call :log "Creating manual backup..."
    call :create_backup
    call :success "Manual backup completed!"
) else if "%command%"=="health" (
    call :log "Performing health check..."
    curl -f http://localhost:8000/health >nul 2>&1
    if not errorlevel 1 (
        call :success "Application is healthy!"
    ) else (
        call :error "Application health check failed!"
    )
) else (
    echo Usage: %0 [deploy^|rollback^|backup^|health]
    echo.
    echo Commands:
    echo   deploy   - Deploy new version ^(default^)
    echo   rollback - Rollback to previous version
    echo   backup   - Create manual backup
    echo   health   - Check application health
    exit /b 1
)

endlocal
