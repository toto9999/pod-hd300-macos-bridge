#!/bin/sh
set -eu
cd "$(dirname "$0")"
printf '%s\n' '가상 입력을 100%로 복구합니다. 현재 설정에 따라 소리가 크게 커질 수 있습니다.'
printf '%s\n' 'GarageBand 모니터링을 끄거나 스피커/헤드폰 볼륨을 먼저 낮춰 주세요.'
printf '%s' '준비됐으면 RESTORE를 입력하고 Return을 누르세요. 그 외 입력은 취소: '
read -r answer
[ "$answer" = RESTORE ] || exit 0
.venv/bin/python "$PWD/src/stop_bridge.py"
build/bridge-level --unity | tee logs/bridge-level-restored.json
.venv/bin/python "$PWD/src/start_bridge.py"
printf '%s\n' '가상 입력은 100%입니다. GarageBand 증폭을 낮게 두고 모니터링 볼륨을 천천히 올려 확인하세요.'
