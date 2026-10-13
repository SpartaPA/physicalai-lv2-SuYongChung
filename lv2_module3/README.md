# lv2_module3 — 모듈 3 과제 (설정값에 따른 Mask·검출 결과 변화 분석)

보고서: [`report.md`](report.md)

## 코드 출처

- `vision_node.py`: 19강(HSV 마스킹·컨투어 검출)과 21강(cv_bridge 노드) 교안 코드를 바탕으로 **직접 구성**했습니다.
  - 튜터 제공 코드가 아니라 교안 기반 자체 구성입니다. (과제 안내의 "Mask 발행 코드 제공" 대신 사용)
  - 교안과 다른 점: Mask 토픽(`/mask`) 발행 추가, 설정값을 ROS 2 파라미터로 노출, EMA 제거, 후보 개수·탈락 사유 로그 추가.
  - HSV 범위와 `min_area` 기본값은 `IRS_ws/opencv/main.py`의 값, 원형도 문턱값 0.6은 19강 교안의 값입니다.
- 원본 교안: 19강 [실습] HSV 마스킹·컨투어 색상 객체 검출, 21강 [실습] cv_bridge ROS2 이미지 토픽 연동
- 과제를 위해 `vision_node.py`는 수정하지 않았습니다. 설정값만 ROS 2 파라미터로 바꿨습니다.

## 실행 환경

| 항목 | 버전 |
|---|---|
| OS | Ubuntu 24.04 LTS |
| ROS 2 | Lyrical |
| Python | 3.12.3 |
| OpenCV | 4.6.0 |
| 입력 | 라이브 Camera (Intel RealSense D435, `realsense2_camera`) |

ROS 2 노드는 ROS가 설치된 시스템 Python으로 실행합니다. 가상환경(venv)을 활성화한 상태에서는 `cv_bridge`와 충돌할 수 있어 사용하지 않았습니다.

## 실행 명령

```bash
# 터미널마다 먼저
source /opt/ros/lyrical/setup.bash

# 터미널 1: 입력 (Camera 드라이버)
ros2 launch realsense2_camera rs_launch.py

# 터미널 2: 비전 노드 (파란색 HSV 값으로 실행. 실험의 기준값 A)
python3 vision_node.py --ros-args \
  -p image_topic:=/camera/camera/color/image_raw \
  -p hsv_lower1:="[100,150,50]" -p hsv_upper1:="[130,255,255]" \
  -p hsv_lower2:="[100,150,50]" -p hsv_upper2:="[130,255,255]"

# 터미널 3: 확인
ros2 topic list -t
ros2 topic info /mask --verbose
ros2 topic echo /detection
ros2 run rqt_image_view rqt_image_view     # /camera/camera/color/image_raw, /mask, /image_annotated 선택
```

코드의 HSV 기본값은 빨강이라, 실험에서는 위처럼 파란 물체용 값을 `-p`로 지정했습니다.

## 설정값 변경·적용 방법

설정값은 ROS 2 파라미터이고 **`vision_node.py`의 코드는 바꾸지 않았습니다**.

| 실험 | 변경 값 | 적용 방법 |
|---|---|---|
| 1 | S 하한 `hsv_lower1/2[1]`: 150 → 200 | 노드를 재시작하며 `-p hsv_lower1:="[100,200,50]" -p hsv_lower2:="[100,200,50]"` 지정. 적용 값은 `ros2 param get`으로 확인 (`results/exp1_params.txt`) |
| 2 | `min_area`: 500.0 → 6000.0 | 실행 중인 노드에 `ros2 param set /color_detector min_area 6000.0`. 적용 값은 `ros2 param get`으로 확인 (`results/exp2_params.txt`) |

- 실험 1에서 `ros2 param set /color_detector hsv_lower1 "[100, 200, 50]"`로 바꾸자 노드가 `inRange`의 타입 에러(`lowerb data type = 9 is not supported`)로 종료되어, HSV 배열 값은 노드 재시작 방식으로 적용했습니다.
- 숫자 하나인 `min_area`는 `ros2 param set`으로 정상 적용되었습니다.

| 파라미터 | 코드 기본값 | 쓰이는 곳 |
|---|---|---|
| `hsv_lower1`, `hsv_upper1` | [0,120,70], [10,255,255] | `make_mask()`의 `inRange` (구간 1) |
| `hsv_lower2`, `hsv_upper2` | [170,120,70], [180,255,255] | `make_mask()`의 `inRange` (구간 2) |
| `min_area` | 500.0 | `detect()`의 면적 필터 (73줄) |
| `min_circularity` | 0.6 | `detect()`의 형상 필터 (76~78줄) |

## 토픽 (실제 사용한 이름)

| 방향 | 토픽 | 타입 |
|---|---|---|
| 구독 | `/camera/camera/color/image_raw` | sensor_msgs/msg/Image (640×480, rgb8) |
| 발행 | `/mask` | sensor_msgs/msg/Image (mono8, 0/255) |
| 발행 | `/detection` | geometry_msgs/msg/PointStamped (픽셀 중심 x, y, z=0; 미검출 시 발행 안 함) |
| 발행 | `/image_annotated` | sensor_msgs/msg/Image (bgr8, 박스·중심점 Overlay) |

## 결과 파일 위치 (`results/`)

| 구분 | 파일 |
|---|---|
| 토픽 정보 | `topic_info.txt`, `raw_header.txt`, `raw_hz.txt`, `mask_hz.txt`, `detection_interface.txt`, `detection_echo.txt` |
| 기준 상태 | `params_baseline.txt`, `detect_log_baseline.txt`, `raw_capture.png`, `mask_capture.png`, `annotated_capture.png` |
| 실험 1 (S 하한) | `exp1_params.txt`, `exp1_{A,B}_{raw,mask,overlay}.png`, `exp1_{A,B}_detect.txt` |
| 실험 2 (`min_area`) | `exp2_params.txt`, `exp2_{A,B}_{raw,mask,overlay}.png`, `exp2_{A,B}_detect.txt`, `exp2_{A,B}_grab.txt` |
| 목표 없음 확인 | `no_target_{raw,mask,overlay}.png`, `no_target_detect.txt`, `no_target_params.txt`, `no_target_nodes.txt`, `no_target_hz_{raw,mask}.txt`, `no_target_grab.txt` |

- `*_grab.txt`의 stamp는 캡처한 Raw, Mask, Overlay 메시지의 시각입니다.
- 이미지 캡처 중 일부는 토픽을 구독해 PNG로 저장하는 임시 보조 스크립트를 사용했습니다(저장소에는 포함하지 않음).
