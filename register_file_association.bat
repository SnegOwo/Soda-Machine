@echo off
title "ImagesSH - Association de fichiers .eau, .soda et .beer"
echo =====================================================
echo   Association des fichiers .eau, .soda et .beer a ImagesSH
echo =====================================================
echo.
echo Ce script va associer les extensions .eau, .soda et .beer
echo a l'executable ImagesSH.exe.
echo.
echo ATTENTION : Ce script doit etre execute en tant
echo qu'ADMINISTRATEUR pour modifier le registre.
echo.
echo Si vous ne l'avez pas deja fait, faites un clic droit
echo sur ce fichier et choisissez "Executer en tant
echo qu'administrateur".
echo.
echo =====================================================
echo.

:: Demander le chemin de ImagesSH.exe
set /p EXE_PATH="Entrez le chemin de ImagesSH.exe (ou appuyez sur Entree pour utiliser dist\ImagesSH.exe) : "
if "%EXE_PATH%"=="" set EXE_PATH=%~dp0dist\ImagesSH.exe

if not exist "%EXE_PATH%" (
    echo.
    echo [ERREUR] Fichier introuvable : %EXE_PATH%
    echo.
    echo Veuillez d'abord builder l'executable avec :
    echo   python build_exe.py
    echo.
    pause
    exit /b 1
)

echo.
echo Chemin de l'executable : %EXE_PATH%
echo.
echo Ajout des associations dans le registre...
echo.

:: .eau
reg add "HKEY_CLASSES_ROOT\.eau" /ve /d "ImagesSH.eau" /f >nul
reg add "HKEY_CLASSES_ROOT\ImagesSH.eau" /ve /d "Image EAU (ImagesSH)" /f >nul
reg add "HKEY_CLASSES_ROOT\ImagesSH.eau\shell\open\command" /ve /d "\"%EXE_PATH%\" \"%%1\"" /f >nul
reg add "HKEY_CLASSES_ROOT\ImagesSH.eau\DefaultIcon" /ve /d "\"%EXE_PATH%\",0" /f >nul
echo   [OK] .eau associe

:: .soda
reg add "HKEY_CLASSES_ROOT\.soda" /ve /d "ImagesSH.soda" /f >nul
reg add "HKEY_CLASSES_ROOT\ImagesSH.soda" /ve /d "Image SODA (ImagesSH)" /f >nul
reg add "HKEY_CLASSES_ROOT\ImagesSH.soda\shell\open\command" /ve /d "\"%EXE_PATH%\" \"%%1\"" /f >nul
reg add "HKEY_CLASSES_ROOT\ImagesSH.soda\DefaultIcon" /ve /d "\"%EXE_PATH%\",0" /f >nul
echo   [OK] .soda associe

:: .beer
reg add "HKEY_CLASSES_ROOT\.beer" /ve /d "ImagesSH.beer" /f >nul
reg add "HKEY_CLASSES_ROOT\ImagesSH.beer" /ve /d "Image BEER (ImagesSH)" /f >nul
reg add "HKEY_CLASSES_ROOT\ImagesSH.beer\shell\open\command" /ve /d "\"%EXE_PATH%\" \"%%1\"" /f >nul
reg add "HKEY_CLASSES_ROOT\ImagesSH.beer\DefaultIcon" /ve /d "\"%EXE_PATH%\",0" /f >nul
echo   [OK] .beer associe

:: Forcer le rafraichissement de l'Explorateur
echo.
echo Rafraichissement de l'Explorateur Windows...
ie4uinit.exe -show >nul 2>&1
taskkill /f /im explorer.exe >nul 2>&1
start explorer.exe

echo.
echo =====================================================
echo   [SUCCES] Associations creees avec succes !
echo =====================================================
echo.
echo Vous pouvez maintenant double-cliquer sur un fichier
echo .eau, .soda ou .beer pour l'ouvrir avec ImagesSH.exe
echo.
pause