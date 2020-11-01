@echo off
setlocal
cd /d %~dp0
del hexhubs.pk3 2>nul
mkdir tmp\maps 2>nul
pushd tmp
pushd maps
%~dp0\hexenhubmerge.py %~dp0\HEXEN.WAD map01.wad -n MAP01 MAP01
%~dp0\hexenhubmerge.py %~dp0\HEXEN.WAD map02.wad -n MAP02 MAP02 MAP03 MAP04 MAP05 MAP06
%~dp0\hexenhubmerge.py %~dp0\HEXEN.WAD map03.wad -n MAP03 MAP13 MAP08 MAP09 MAP10 MAP11 MAP12
%~dp0\hexenhubmerge.py %~dp0\HEXEN.WAD map04.wad -n MAP04 MAP27 MAP32 MAP33 MAP34 MAP28 MAP30 MAP31
%~dp0\hexenhubmerge.py %~dp0\HEXEN.WAD map05.wad -n MAP05 MAP22 MAP21 MAP23 MAP24 MAP25 MAP26
%~dp0\hexenhubmerge.py %~dp0\HEXEN.WAD map06.wad -n MAP06 MAP35 MAP36 MAP38 MAP37 MAP39
%~dp0\hexenhubmerge.py %~dp0\HEXEN.WAD map07.wad -n MAP07 MAP40
popd
7z.exe a -r -tzip ..\hexenhubs.pk3 *
popd
