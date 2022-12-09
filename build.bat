echo off
set actie=%1
set naslagwerk=%2
set arg1=%3
set arg2=%4
set arg3=%5
set arg4=%6

call conda activate moedertabel

if %actie%==topo goto topo
if %actie%==site goto site
echo %actie% niet herkend, kies "topo" of "site"
goto:eof

:topo
call python build_topography.py %naslagwerk%
goto:eof

:site
call python build_site.py %naslagwerk% %arg1% %arg2% %arg3% %arg4%
