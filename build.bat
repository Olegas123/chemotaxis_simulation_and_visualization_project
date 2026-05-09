@echo off
REM build.bat - Build script for Windows
REM Usage: build.bat [target]

setlocal

REM Compiler settings
set CXX=g++
set CXXFLAGS=-O3 -Wall -march=native -fopenmp -ffast-math

REM Directories
set BIN_DIR=bin
set RESULTS_DIR=results
set IC_DIR=ic

REM Check if target is specified
set TARGET=%1
if "%TARGET%"=="" set TARGET=all

REM Create directories
if not exist %BIN_DIR% mkdir %BIN_DIR%
if not exist %RESULTS_DIR% mkdir %RESULTS_DIR%
if not exist %IC_DIR% mkdir %IC_DIR%

echo Created directories: %BIN_DIR%\, %RESULTS_DIR%\, %IC_DIR%\
echo.

REM Build based on target
if "%TARGET%"=="all" goto build_all
if "%TARGET%"=="1d" goto build_1d
if "%TARGET%"=="top" goto build_top
if "%TARGET%"=="side" goto build_side
if "%TARGET%"=="3d" goto build_3d
if "%TARGET%"=="coupled" goto build_coupled
if "%TARGET%"=="ic_gen" goto build_ic_gen
if "%TARGET%"=="clean" goto clean
if "%TARGET%"=="help" goto help

echo Unknown target: %TARGET%
echo Run: build.bat help
goto end

:build_all
echo Building all executables...
call :build_1d
call :build_top
call :build_side
call :build_3d
call :build_coupled
call :build_ic_gen
echo.
echo ===== BUILD COMPLETE =====
echo Executables in: %BIN_DIR%\
echo   - %BIN_DIR%\1d.exe
echo   - %BIN_DIR%\top.exe
echo   - %BIN_DIR%\side.exe
echo   - %BIN_DIR%\3d.exe
echo   - %BIN_DIR%\coupled_2d.exe
echo   - %BIN_DIR%\ic_gen.exe
echo.
echo Next steps:
echo   1. Generate IC: %BIN_DIR%\ic_gen.exe all
echo   2. Run models:
echo      %BIN_DIR%\1d.exe %IC_DIR%\ic_1d.dat
echo      %BIN_DIR%\top.exe %IC_DIR%\ic_polar.dat
echo      %BIN_DIR%\side.exe %IC_DIR%\ic_cyl.dat
echo      %BIN_DIR%\3d.exe %IC_DIR%\master_ic.dat
echo      %BIN_DIR%\coupled_2d.exe %IC_DIR%\ic_polar.dat %IC_DIR%\ic_cyl.dat
goto end

:build_1d
echo Building 1D model...
%CXX% %CXXFLAGS% -o %BIN_DIR%\1d.exe 1D.cpp writer.cpp
if errorlevel 1 (
    echo ERROR: Failed to build 1d.exe
    exit /b 1
)
echo Built: %BIN_DIR%\1d.exe
goto :eof

:build_top
echo Building 2D polar model...
%CXX% %CXXFLAGS% -o %BIN_DIR%\top.exe 2Dtop.cpp writer.cpp
if errorlevel 1 (
    echo ERROR: Failed to build top.exe
    exit /b 1
)
echo Built: %BIN_DIR%\top.exe
goto :eof

:build_side
echo Building 2D cylindrical model...
%CXX% %CXXFLAGS% -o %BIN_DIR%\side.exe 2Dside.cpp writer.cpp
if errorlevel 1 (
    echo ERROR: Failed to build side.exe
    exit /b 1
)
echo Built: %BIN_DIR%\side.exe
goto :eof

:build_coupled
echo Building coupled 2D model...
%CXX% %CXXFLAGS% -o %BIN_DIR%\coupled_2d.exe 2Dcombined.cpp writer.cpp
if errorlevel 1 (
    echo ERROR: Failed to build coupled_2d.exe
    exit /b 1
)
echo Built: %BIN_DIR%\coupled_2d.exe
goto :eof

:build_3d
echo Building 3D cylindrical polar model...
%CXX% %CXXFLAGS% -o %BIN_DIR%\3d.exe 3D.cpp writer.cpp
if errorlevel 1 (
    echo ERROR: Failed to build 3d.exe
    exit /b 1
)
echo Built: %BIN_DIR%\3d.exe
goto :eof

:build_ic_gen
echo Building IC generator...
%CXX% %CXXFLAGS% -o %BIN_DIR%\ic_gen.exe initialConditions.cpp
if errorlevel 1 (
    echo ERROR: Failed to build ic_gen.exe
    exit /b 1
)
echo Built: %BIN_DIR%\ic_gen.exe
goto :eof

:clean
echo Cleaning executables...
if exist %BIN_DIR% (
    del /Q %BIN_DIR%\*.exe 2>nul
    echo Removed executables from %BIN_DIR%\
) else (
    echo %BIN_DIR%\ directory doesn't exist
)
goto end

:help
echo Available targets:
echo   build.bat          - Build all executables (default)
echo   build.bat all      - Build all executables
echo   build.bat 1d       - Build only 1D model
echo   build.bat top      - Build only 2D polar model (with spatiotemporal)
echo   build.bat side     - Build only 2D cylindrical model (with spatiotemporal)
echo   build.bat 3d       - Build only 3D cylindrical polar model
echo   build.bat coupled  - Build only coupled 2D model
echo   build.bat ic_gen   - Build only IC generator
echo   build.bat clean    - Remove executables
echo   build.bat help     - Show this help
echo.
echo Project structure:
echo   bin\               - Executables
echo   results\           - Simulation outputs (snapshots + spatiotemporal)
echo   ic\                - Initial conditions
echo.
echo Models:
echo   1D                 - Simple 1D periodic domain
echo   2D polar           - Top disk (polar coordinates)
echo   2D cylindrical     - Side surface (unwrapped cylinder)
echo   3D                 - Full 3D cylindrical polar coordinates
echo   Coupled 2D         - Combined polar + cylindrical
echo.
echo 2D models include spatiotemporal data saving!
goto end

:end
endlocal