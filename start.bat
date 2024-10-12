@ECHO OFF
@REM ECHO please open nginx.exe, after press any key to continue
@REM pause   
@REM keep exit code of start.py
set repeated_failure=0
set github_token=PUT TOKEN HERE

py start.py --no-debug
set EXIT_CODE=%ERRORLEVEL%

ECHO Server stopped with %EXIT_CODE%


if %EXIT_CODE% eq 1 (
    set /a repeated_failure+=1
) else (
    set repeated_failure=0
)


if %EXIT_CODE% eq 1 && %repeated_failure% lss 3 (
    ECHO start.py is restarting... Attempt %repeated_failure%
    goto :BEGIN
) else if %EXIT_CODE% eq 1 (
    ECHO start.py failed to start after %repeated_failure% attempts, waiting 5 minutes before pulling from github and retrying...
    timeout /t 300
    goto :FETCH_FROM_GITHUB
) else if %EXIT_CODE% eq 2 (
    ECHO start.py failed with exit code %EXIT_CODE%
    goto :FETCH_FROM_GITHUB
) else (
    ECHO start.py exited with code %EXIT_CODE% - exiting...
)
goto :END

:FETCH_FROM_GITHUB
ECHO Pulling from github...
@REM IT IS IMPERATIVE THAT THE FOLLOWING LINE IS NEVER LEAKED BECAUSE I CANNOT BE FUCKED USING SYSTEM VARIABLES
git pull https://%github_token%@github.com/jh1236/matchmaking
ECHO Retrying start.py... Attempt %repeated_failure%
goto :BEGIN


:END
pause