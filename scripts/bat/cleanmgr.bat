@echo off
title mgr

:CleanMGR
:CleanMGR
cls
echo ==================================================
echo             Clean MGR
echo ==================================================
echo.
echo - Iniciando la herramienta de limpieza de disco...
timeout /t 1 /nobreak >nul

cleanmgr /sagerun:1

echo.
echo Hecho!
pause
exit