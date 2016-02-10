@echo off 
REM Download and install curl  http://curl.haxx.se/dlwiz/?type=bin&os=Win32 to use this script 
REM Envinfo is returned in a single line RAPTURE_HOME,http://<demo env address>:8665/rapture|RAPTURE_USER,<username>

ECHO ***************************************************************
ECHO Starting Rapture Demo Client Environment Setup
SET "REFLEX_RUNNER_LATEST=https://github.com/RapturePlatform/Rapture/releases/latest"
SET "REFLEX_RUNNER_DOWNLOAD_PREFIX=https://github.com/RapturePlatform/Rapture/releases/download"
SET "RAPTURE_DEMO_HOME_DIR=%CD%\.."

REM "*************************************************************"
REM get etienne credentials to setup env info
SET "etienneurl=etn.incapture.net"
SET /P user=Enter Etienne User: 
SET /P pass=Enter Etienne Password: 

REM "*************************************************************"
REM create a hashed password usin md5.exe
%CD%\tools\md5 -l -d%pass% > temp.txt
SET /P hashpass=<temp.txt
DEL temp.txt

REM "*************************************************************"
REM setup urls for curl
SET "LOGIN_URL=http://%etienneurl%:8080/login/login?user=%user%^&password=%hashpass%"
SET "SERVICE_URL=http://%etienneurl%:8080/curtisscript/getEnvInfo?username=%user%"

REM "*************************************************************"
REM call login url to get cookie and then get the enn details 
curl --silent --cookie-jar cookiefile.txt %LOGIN_URL% > nul 2>&1
curl --silent --cookie cookiefile.txt %SERVICE_URL% > tmpenvinfo.txt

REM "*************************************************************"
REM split the line into RAPTURE_HOST and RAPTURE_USER env vars
FOR /F "tokens=1 delims=|" %%a in (tmpenvinfo.txt) DO SET LINE1=%%a
FOR /F "tokens=2 delims=|" %%b in (tmpenvinfo.txt) DO SET LINE2=%%b
FOR /F "tokens=2 delims=," %%G IN ("%LINE1%") DO SET RAPTURE_HOST=%%G 
FOR /F "tokens=2 delims=," %%H IN ("%LINE2%") DO SET RAPTURE_USER=%%H 
DEL tmpenvinfo.txt

REM "*************************************************************"
REM Download the latest reflexrunner zip
REM returns the redirect url for the latest release
curl --silent %REFLEX_RUNNER_LATEST% > rrlocation.txt
REM extract the url from html file in rrlocation.txt
FOR /F delims^=^"^ tokens^=2 %%M in (rrlocation.txt) DO SET RRUNNER_LATEST_REDIRECT_URL=%%M
FOR /F "tokens=7 delims=/" %%N IN ("%RRUNNER_LATEST_REDIRECT_URL%") DO SET RRUNNER_LATEST_TAG=%%N
set "RRUNNER_LATEST_DOWNLOAD_URL=%REFLEX_RUNNER_DOWNLOAD_PREFIX%/%RRUNNER_LATEST_TAG%/ReflexRunner-%RRUNNER_LATEST_TAG%.zip"
REM If reflexrunner.zip file already exists then dont download it
IF NOT EXIST %CD%\ReflexRunner-%RRUNNER_LATEST_TAG%.zip (
	ECHO Starting download of ReflexRunner version %RRUNNER_LATEST_TAG% at %TIME%
	curl -qLSs -O %RRUNNER_LATEST_DOWNLOAD_URL%
	ECHO Finished download of ReflexRunner version %RRUNNER_LATEST_TAG% at %TIME%
	REM unzip it. -bd:hide % indicator -y:assume yes to all prompts
	%CD%\tools\7z x -bd -y ReflexRunner-%RRUNNER_LATEST_TAG%.zip > nul 2>&1
	ECHO ReflexRunner-%RRUNNER_LATEST_TAG%.zip unzipped to %CD%\ReflexRunner-%RRUNNER_LATEST_TAG%
) ELSE (
	ECHO Skipping download of ReflexRunner version %RRUNNER_LATEST_TAG% as it already exists
)
DEL rrlocation.txt

REM set the csv path and reflex runner bin
SET "RAPTURE_TUTORIAL_CSV=%RAPTURE_DEMO_HOME_DIR%\Intro01\resources\introDataInbound.csv"
SET "PATH=%PATH%;%RAPTURE_DEMO_HOME_DIR%\Setup\ReflexRunner-%RRUNNER_LATEST_TAG%\bin"

REM leave user in home dir
cd %RAPTURE_DEMO_HOME_DIR%
ECHO Setup completed
ECHO ***************************************************************

REM clean up variables
SET "LINE1="
SET "LINE2="
SET "LOGIN_URL="
SET "SERVICE_URL="
SET "RRUNNER_LATEST_DOWNLOAD_URL="
SET "REFLEX_RUNNER_DOWNLOAD_PREFIX="
SET "RRUNNER_LATEST_TAG="
SET "REFLEX_RUNNER_LATEST="
SET "RRUNNER_LATEST_REDIRECT_URL="