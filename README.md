# POD HD300 macOS Bridge

**Apple Silicon Mac에서 Line 6 POD HD300의 USB 오디오를 GarageBand 입력으로 연결하는 실험 프로젝트입니다.**

An experimental user-space USB audio receiver and Core Audio bridge for the Line 6 POD HD300 on Apple Silicon macOS.

HD300 USB 입력을 받아 48kHz·24비트 스테레오로 해석하고, 별도로 빌드한 BlackHole 기반 가상 장치
**POD HD300 USB Bridge 2ch**로 전달합니다. GarageBand 등은 이 가상 장치를 입력으로 선택합니다.

> **실험판:** 장치 인식과 실제 데이터 전송은 확인했지만, 장시간 연주·모든 Mac·모든 DAW에서의
> 안정성을 보장하지 않습니다. 끊김과 USB 재연결 문제가 관측됐으며 복구 처리를 개선 중입니다.
> 배포 파일은 Developer ID 서명 및 Apple 공증을 받지 않았습니다.

## 지원 범위

| 항목 | 상태 |
| --- | --- |
| 장치 | POD HD300, USB `0e41:5057` |
| 플랫폼 | Apple Silicon / arm64 macOS |
| 실제 시험 환경 | macOS 27.2, GarageBand |
| 입력 | USB 48kHz, stereo, packed signed PCM24 little-endian |
| 가상 장치 | 44.1kHz / 48kHz, stereo float32 |
| Intel Mac / Windows / Linux 패키지 | 제공하지 않음 |
| HD400·HD500 등 다른 모델 | 미검증·지원하지 않음 |
| USB를 통한 HD300 재생 출력 | 구현하지 않음 |
| 프리셋 편집·펌웨어 업데이트 | 구현하지 않음 |

## 다운로드 설치

1. [Releases](https://github.com/toto9999/pod-hd300-macos-bridge/releases)에서
   `pod-hd300-macos-bridge-…-arm64.zip`을 다운로드해 **계속 사용할 로컬 폴더**에 풉니다.
2. `Setup.command`를 실행합니다. 인터넷 연결이 필요하며 uv·Python 3.12·고정된 의존성을
   **그 폴더 안에만** 설치합니다. 셸 PATH나 전역 Python은 변경하지 않습니다.
3. `Install Bridge.command`를 실행해 HAL 플러그인을 설치하고 관리자 인증을 완료합니다.
   Core Audio가 재시작되어 재생 중인 소리가 잠시 중단됩니다.
4. HD300을 연결하고 `HD300 Control.command`를 실행한 뒤 **시작**을 누릅니다.
5. GarageBand를 완전히 종료했다가 다시 열고 **설정 → 오디오/MIDI**에서 다음을 선택합니다.
   - 입력: **POD HD300 USB Bridge 2ch**
   - 출력: Mac의 스피커 또는 유선 헤드폰
6. 오디오 트랙 입력을 **1(모노)** 또는 **1+2(스테레오)**로 선택하고 필요하면 입력 모니터링을 켭니다.

macOS가 다운로드한 공증되지 않은 파일을 차단할 수 있습니다. 배포 체크섬과 소스를 확인하세요.
전역 보안 기능을 끄는 설치 방법은 제공하지 않습니다. 소스에서 직접 빌드할 수도 있습니다.

## 소스에서 설치

Git과 Apple Command Line Tools가 필요합니다. 전체 Xcode 앱은 필요하지 않습니다.

```sh
git clone --recurse-submodules https://github.com/toto9999/pod-hd300-macos-bridge.git
cd pod-hd300-macos-bridge
./Setup.command
./Install\ Bridge.command
./HD300\ Control.command
```

다른 위치에서 이미 복제했다면 `git submodule update --init --recursive`로 BlackHole 소스를 준비합니다.
GitHub의 자동 생성 Source ZIP에는 서브모듈 내용이 없으므로, 일반 사용자는 Releases의 전용 ZIP을 사용하세요.

## 조절창

- **지연 모드:** 안정 / 낮은 지연 / 최소 지연. FIFO 목표는 각각 512/256/128 프레임
  (USB 48kHz 기준 약 10.7/5.3/2.7ms)입니다.
- **적응형 안정화:** 10초 안에 버퍼 부족이 두 번 이상 발생하면 64프레임씩 늘리고,
  60초간 안정되면 다시 선택한 목표까지 줄입니다.
- **추가 증폭:** −12~+18dB. 초기값 0dB이며 점진적으로 적용합니다. 0dBFS 초과를 경고합니다.
- **가상 입력 100% 복구:** 이 가상 장치의 볼륨 곡선에서 75%는 약 −16dB입니다.
  복구 전에는 출력 볼륨을 낮추고, 조절창의 확인 안내를 따르세요.
- **입력 미터:** 실제 USB 입력과 추가 증폭·가상 장치 감쇠를 고려한 예상 피크입니다.
  GarageBand 트랙 플러그인이나 스피커까지 측정하는 미터는 아닙니다.

설정은 `settings.json`에 저장됩니다. **창을 닫아도 전송은 계속됩니다.** 중지는 창의 중지 버튼이나
`Stop Bridge.command`로 합니다. 자동 로그인 실행 항목은 설치하지 않습니다.

## 지연과 알려진 한계

USB 요청은 1ms, Core Audio 출력 블록은 64프레임입니다. 한 시험 환경에서 낮은 한 자릿수 ms의
FIFO와 약 1.45ms의 출력 버퍼를 관측했습니다. **전체 연주→GarageBand→스피커 왕복 지연을 측정한 값이 아닙니다.**
작은 버퍼는 CPU·USB·DAW 상태에 따라 끊길 수 있습니다. 이 경우 안정 모드부터 사용하세요.

- 한때 USB 수신이 `LIBUSB_ERROR_OTHER`로 종료된 문제가 있었습니다. 현재는 최대 3회 연속 재연결합니다.
- 소비자가 멈췄을 때 약 734ms의 오래된 오디오가 쌓인 문제가 있었습니다. 현재는 과도한 큐를 버리고
  최신 입력으로 복귀하며 짧은 크로스페이드를 적용합니다. 그동안 잃은 오디오는 복원하지 못합니다.
- 장치 이름은 수신 프로그램이 중지돼도 DAW 목록에 남습니다. 조절창의 실제 연결 상태를 확인하세요.
- 장치·샘플 속도를 변경했다면 중지→시작으로 재연결하세요. 모든 핫플러그 상황의 복구는 미검증입니다.
- HD300에서 이미 처리된 신호에 GarageBand 앰프·페달을 다시 적용하면 의도와 다른 소리가 날 수 있습니다.

## 제거

1. 조절창에서 중지를 누르고 조절창을 닫습니다.
2. `Uninstall Bridge.command`를 실행하고 관리자 인증을 완료합니다.
3. HAL 플러그인은 `uninstalled/`로 회수되고 설치 영수증과 선택적 검사 앱의 마이크 허용 기록이 정리됩니다.
4. 그 뒤 프로젝트 폴더 하나를 휴지통으로 옮깁니다.

시스템에 설치하는 파일은 `/Library/Audio/Plug-Ins/HAL/HD300USBBridge.driver`입니다.
설치 영수증 ID는 `local.hd300lab.USBBridge`입니다. 커널 확장·SIP 변경·로그인 항목은 사용하지 않습니다.
다른 BlackHole 설치나 다른 오디오 드라이버는 제거하지 않습니다.

## 개발과 진단

```sh
./run.sh start
./run.sh stop
./run.sh bridge --list-devices
# 직접 WAV 녹음 전에는 브리지를 중지합니다.
./run.sh record --seconds 10
.venv/bin/python src/build_all.py
.venv/bin/python -m unittest discover -s src -p 'test_*.py'
```

| 경로 | 내용 |
| --- | --- |
| `src/` | USB 수신, FIFO·리샘플러, 조절창, 빌드 및 검사 코드 |
| `vendor/linux-line6/` | USB 프로토콜 참고 원문 및 해시 |
| `vendor/BlackHole/` | 고정된 BlackHole 서브모듈 |
| `settings.example.json` | 추가 증폭 없는 안전한 시작 설정 |
| `build/` | 로컬 빌드 산출물·설치 패키지 |
| `logs/`, `recordings/` | 로컬 상태·진단·녹음; Git에서 제외 |

`HD300 Audio Check.app`은 선택적인 진단 앱이며 가상 입력 검사에 마이크 권한이 필요합니다.
일반 USB 브리지와 조절창은 이 검사 앱의 마이크 권한을 요구하지 않습니다.
재배포 파일 생성과 검사 범위는 [배포 안내](docs/RELEASING.md)를 참고하세요.

## 라이선스와 출처

프로젝트 자체 코드는 **GPL-2.0-only**입니다. 별도 구성요소인 BlackHole HAL 플러그인은
**GPL-3.0**이며 해당 라이선스를 유지합니다. Linux 참고 원문과 패키지별 고지도 유지합니다.
상세 범위는 [LICENSE](LICENSE)와 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)를 참고하세요.

Line 6 또는 Apple의 공식 소프트웨어가 아니며, 제품명은 각 소유자의 상표입니다.
