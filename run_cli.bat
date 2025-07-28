@echo off
echo Image Base64 Converter - CLI Mode
echo.
echo Usage examples:
echo   Convert single image: python main.py image.png
echo   Convert with output:  python main.py image.png -o output.txt
echo   Convert directory:    python main.py images/
echo   Show help:           python main.py -h
echo.
echo Enter your command (or press Enter to exit):
set /p command=
if "%command%"=="" goto end
python main.py %command%
echo.
pause
:end