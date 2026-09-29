# LV2 Module 1 — OpenCR·다이나믹셀 통합
<br>
**작성자: 정수용**

## 장비 및 환경

- 라즈베리파이 OS: Ubuntu Server 22.04 (Ubuntu 22.04.5 LTS) / 아키텍처 aarch64 (호스트명 `pa24`)
- 제어기: OpenCR 1.0
- 모터: 다이나믹셀 1개 (모델 XM430-W210, ID 1, Protocol 2.0, 1 Mbps)
- PC 역할: SSH 접속 전용 (펌웨어 업로드·시리얼 송수신·로그 저장은 모두 라즈베리파이에서 수행)
- OpenCR 연결 포트: `/dev/ttyACM0` (사용자 `pa24`가 `dialout` 그룹에 포함됨)

## 실행 방법

1. **SSH 접속**: PC에서 `ssh pa24@<라즈베리파이 IP>`로 접속하고, `whoami`(→ `pa24`)와 `id -nG`(→ `dialout` 포함)로 접속과 포트 권한을 확인했다. 이후 모든 작업은 SSH 터미널 안에서만 수행했다.
2. **OpenCR 펌웨어 업로드**: 제공 바이너리 대신 **직접 빌드**한 `output/opencr_position_p.ino.bin`(103KB)을 사용했다. 제공 바이너리가 XM430-W350/ID 12 기준이라 본인 장비(XM430-W210, ID 1)에 맞춰 `DXL_ID`를 수정했고(모델 검사는 우회하지 않음), 상태 확인용 `?` 명령을 추가했다. 빌드·업로드는 `OpenCR_빌드_업로드_가이드.md` 절차(arduino-cli + arm-none-eabi 툴체인 + `opencr_ld`)를 따랐다.
   - 업로드 명령: `"$UPLOADER" "$PORT" 115200 "$BASE/output/opencr_position_p.ino.bin" 1`
   - 성공 확인: `CRC OK 9B81E2 9B81E2` / `[OK] Download`, 이후 `?` 입력 시 `READY: ...` 출력
3. **목표 입력 실행**: 시리얼 터미널을 열고 `s <Kp> <속도 상한 deg/s> <목표각 deg>` 형식으로 입력한다.
   - 터미널: `python3 -m serial.tools.miniterm /dev/ttyACM0 115200 --eol LF -e`
   - 실행 A: `s 0.5 15 20` (Kp 0.5, 속도 상한 15 deg/s, 목표각 20°)
   - 실행 B: `s 1.0 15 20` (Kp만 1.0으로 변경, 나머지 동일)
   - 종료: `x` 입력 → `STOP: user` 확인
4. **로그 저장 방법**: 터미널 출력을 `| tee ~/실행A.log`(실행 B는 `~/실행B.log`)로 라즈베리파이에 저장한 뒤, 목표 변경 이후 측정값을 발췌해 `results/`에 정리했다.

## 결과 파일 위치

| 경로 | 내용 |
|---|---|
| [`results/환경확인.txt`](results/환경확인.txt) | 호스트명, Ubuntu 버전, 아키텍처, 사용 포트 |
| [`results/upload.log`](results/upload.log) | 라즈베리파이에서 수행한 업로드와 성공 확인 |
| [`results/실행A.log`](results/실행A.log) | 실행 A(Kp 0.5) 목표 변경 이후 측정값과 정지 확인 |
| [`results/실행B.log`](results/실행B.log) | 실행 B(Kp 1.0) 목표 변경 이후 측정값과 정지 확인 |

## 기록 구분

- 문제 1~3의 표와 로그는 본인 장비에서 실제로 측정한 결과이다.
- 문제 4의 기록은 과제에서 제공한 가상 기록이며 실측 결과가 아니다.

## 관련 문서

- 문제별 상세 설정·기록·해석: [report.md](report.md)
