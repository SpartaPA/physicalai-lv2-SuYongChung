#!/usr/bin/env python3
"""모듈 3 과제용 비전 노드 (19강 검출기 + 21강 cv_bridge 노드를 합쳐 구성한 것).

Raw Image 구독 → Mask 생성 → 컨투어 검출 → Mask / 검출 결과 / Overlay 발행.
교안 코드에서 바꾼 점 (보고서·README에 출처로 기록할 것):
  - 교안 노드에 없던 Mask 토픽(/mask)을 발행한다.
  - 설정값(HSV 범위, min_area, 원형도 문턱값)을 ROS 2 파라미터로 노출한다.
  - EMA는 넣지 않았다 (A/B 비교 시 이전 프레임 값이 섞이지 않게 하기 위해).
  - 후보 개수·탈락 사유를 로그로 남긴다 (비교 근거용).
토픽 이름은 파라미터로 바꿀 수 있다 (기본값은 교안의 예시 이름).
"""
import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from geometry_msgs.msg import PointStamped
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image


class VisionNode(Node):
    def __init__(self):
        super().__init__("color_detector")
        self.bridge = CvBridge()

        # ---- 설정값 (ros2 run ... --ros-args -p name:=value 또는 ros2 param set) ----
        # 기본값: HSV·min_area는 IRS_ws/opencv/main.py의 값, 원형도는 19강 교안의 값
        self.declare_parameter("hsv_lower1", [0, 120, 70])      # 빨강 구간 1 하한 [H, S, V]
        self.declare_parameter("hsv_upper1", [10, 255, 255])    # 빨강 구간 1 상한
        self.declare_parameter("hsv_lower2", [170, 120, 70])    # 빨강 구간 2 하한 (H가 감기는 쪽)
        self.declare_parameter("hsv_upper2", [180, 255, 255])   # 빨강 구간 2 상한
        self.declare_parameter("min_area", 500.0)               # 면적 필터 [px^2]
        self.declare_parameter("min_circularity", 0.6)          # 형상 필터 (0~1)
        self.declare_parameter("image_topic", "/image_raw")
        self.declare_parameter("mask_topic", "/mask")
        self.declare_parameter("detection_topic", "/detection")
        self.declare_parameter("annotated_topic", "/image_annotated")

        p = self.get_parameter
        self.sub = self.create_subscription(
            Image, p("image_topic").value, self.on_image, qos_profile_sensor_data)
        self.pub_mask = self.create_publisher(Image, p("mask_topic").value, 1)
        self.pub_pt = self.create_publisher(PointStamped, p("detection_topic").value, 10)
        self.pub_dbg = self.create_publisher(Image, p("annotated_topic").value, 1)
        self.get_logger().info(
            f"subscribe {p('image_topic').value} -> publish "
            f"{p('mask_topic').value}, {p('detection_topic').value}, {p('annotated_topic').value}")

    # ------------------------------------------------------------------ 비전 로직
    def make_mask(self, frame_bgr):
        """블러 → HSV → inRange(빨강 2구간 OR) → 열림 → 닫힘 (19강 make_mask)."""
        p = self.get_parameter
        blur = cv2.GaussianBlur(frame_bgr, (5, 5), 0)
        hsv = cv2.cvtColor(blur, cv2.COLOR_BGR2HSV)
        m1 = cv2.inRange(hsv, np.array(p("hsv_lower1").value), np.array(p("hsv_upper1").value))
        m2 = cv2.inRange(hsv, np.array(p("hsv_lower2").value), np.array(p("hsv_upper2").value))
        mask = cv2.bitwise_or(m1, m2)
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)
        return mask

    def detect(self, mask):
        """컨투어 → 면적 필터 → 원형도 필터 → 가장 큰 후보 선택 (19강 detect)."""
        p = self.get_parameter
        min_area = p("min_area").value
        min_circ = p("min_circularity").value
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        best, n_small, n_round = None, 0, 0
        for c in cnts:
            area = cv2.contourArea(c)
            if area < min_area:
                n_small += 1
                continue
            peri = cv2.arcLength(c, True)
            circ = 4 * np.pi * area / (peri * peri + 1e-9)
            if circ < min_circ:
                n_round += 1
                continue
            if best is None or area > best[0]:
                best = (area, c)
        stats = {"contours": len(cnts), "drop_area": n_small, "drop_circ": n_round}
        if best is None:
            return None, stats
        m = cv2.moments(best[1])
        cx, cy = m["m10"] / m["m00"], m["m01"] / m["m00"]
        bbox = cv2.boundingRect(best[1])
        return {"cx": cx, "cy": cy, "bbox": bbox, "area": best[0]}, stats

    # ------------------------------------------------------------------ ROS 배관
    def on_image(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        mask = self.make_mask(frame)
        r, st = self.detect(mask)

        mask_msg = self.bridge.cv2_to_imgmsg(mask, "mono8")
        mask_msg.header = msg.header
        self.pub_mask.publish(mask_msg)

        dbg = frame.copy()
        if r:
            pt = PointStamped()
            pt.header = msg.header
            pt.point.x, pt.point.y = r["cx"], r["cy"]
            self.pub_pt.publish(pt)
            x, y, w, h = r["bbox"]
            cv2.rectangle(dbg, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.circle(dbg, (int(r["cx"]), int(r["cy"])), 6, (0, 255, 0), -1)
            self.get_logger().info(
                f"DETECT cx={r['cx']:.1f} cy={r['cy']:.1f} area={r['area']:.0f} "
                f"contours={st['contours']} drop_area={st['drop_area']} drop_circ={st['drop_circ']}",
                throttle_duration_sec=0.5)
        else:
            self.get_logger().info(
                f"NO DETECTION contours={st['contours']} drop_area={st['drop_area']} "
                f"drop_circ={st['drop_circ']}", throttle_duration_sec=0.5)
        dbg_msg = self.bridge.cv2_to_imgmsg(dbg, "bgr8")
        dbg_msg.header = msg.header
        self.pub_dbg.publish(dbg_msg)


def main():
    rclpy.init()
    node = VisionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
