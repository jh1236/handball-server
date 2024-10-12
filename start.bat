@ECHO OFF
ECHO Please make sure nginx is running, routing port 80 to 8080
timeout t/ 30

set repeated_failure=0
set github_token=PUT TOKEN HERE

:BEGIN
py start.py --no-debug
set EXIT_CODE=%ERRORLEVEL%

ECHO start.py exited with exit code %EXIT_CODE%


if %EXIT_CODE% == 1 (
    set /a repeated_failure+=1
) else (
    set repeated_failure=0
)

if %EXIT_CODE% == 1 goto :RESTART
if %EXIT_CODE% == 2 goto :UPDATE
ECHO Server has been stopped.
goto :END

:RESTART
if %repeated_failure% lss 3 (
    ECHO start.py is restarting... Attempt %repeated_failure%
) else (
    ECHO start.py failed to start after %repeated_failure% attempts, waiting 5 minutes before pulling from github and retrying...
    timeout /t 300
    goto :UPDATE
)
goto :BEGIN

:UPDATE
ECHO Pulling from github...
git pull https://%github_token%@github.com/jh1236/matchmaking UPDATE
ECHO Retrying start.py... Attempt %repeated_failure%
goto :BEGIN


:END
pause