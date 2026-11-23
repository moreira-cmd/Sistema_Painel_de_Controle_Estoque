@echo off
rem Cria o atalho "ArtGlow Estoque" (com a logo) na Area de Trabalho. Rode uma vez so.
set "PASTA=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$d=[Environment]::GetFolderPath('Desktop'); $s=(New-Object -ComObject WScript.Shell).CreateShortcut($d+'\ArtGlow Estoque.lnk'); $s.TargetPath='%PASTA%iniciar.bat'; $s.WorkingDirectory='%PASTA%'; $s.IconLocation='%PASTA%artglow.ico'; $s.Description='ArtGlow - Controle de Estoque'; $s.Save()"
if errorlevel 1 (
    echo Nao foi possivel criar o atalho.
) else (
    echo Atalho "ArtGlow Estoque" criado na Area de Trabalho.
)
pause
