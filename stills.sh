#!/bin/bash
# usage: stills.sh <outdir> "<sec sec ...>" [extra build.py args]   -> half-size test stills + contact sheet <outdir>/sheet.jpg
cd "/d/CLAUDE OPUS REMOTION/fps-ruined-hall" || exit 1
cat parts/a_header.py parts/b_timeline.py parts/c_scene.py parts/d_rig.py > build.py
out=$1; secs=$2; shift 2
mkdir -p "$out"
args=(); ins=(); n=0
for s in $secs; do args+=(--still "$s"); ins+=(-i "$(printf '%s/still_%05.2f.png' "$out" "$s")"); n=$((n+1)); done
"/d/CLAUDE OPUS REMOTION/tools/blender/blender-4.5.15-windows-x64/blender.exe" -b --factory-startup -P build.py -- --out "$out" --pct 50 --samples 48 "${args[@]}" "$@" > "$out/log.txt" 2>&1
grep -E "Error|Traceback|PLANT|  File " "$out/log.txt"
cols=2; [ $n -gt 6 ] && cols=3
rows=$(( (n + cols - 1) / cols ))
if [ $((rows*cols)) -eq $n ]; then ffmpeg -v error -y "${ins[@]}" -filter_complex "xstack=inputs=$n:grid=${cols}x${rows}" "$out/sheet.jpg"; else echo "sheet needs $((rows*cols)) stills"; fi
