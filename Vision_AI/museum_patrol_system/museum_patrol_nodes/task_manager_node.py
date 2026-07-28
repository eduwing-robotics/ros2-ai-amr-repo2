"""Central task manager for museum patrol operations."""

import time
from enum import Enum
from typing import Dict, Optional

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Bool, Float32, String

from museum_patrol_system.msg import MuseumCommand, MuseumState


class ScenarioId(str, Enum):
    """Five museum patrol scenarios plus idle."""

    IDLE = 'idle'
    EXHIBIT_CONTACT = 'exhibit_contact'       # 전시품 접촉
    BATTERY_HANDOFF = 'battery_handoff'       # 배터리 부족 임무 인계
    NIGHT_INTRUDER = 'night_intruder'         # 야간 침입자 감지
    EXHIBIT_LOSS = 'exhibit_loss'             # 전시품 분실
    FIRE_RESPONSE = 'fire_response'           # 화재 의심 대응


SCENARIO_PRIORITY = {
    ScenarioId.IDLE: 0,
    ScenarioId.BATTERY_HANDOFF: 1,
    ScenarioId.EXHIBIT_CONTACT: 2,
    ScenarioId.EXHIBIT_LOSS: 3,
    ScenarioId.NIGHT_INTRUDER: 4,
    ScenarioId.FIRE_RESPONSE: 5,
}

SCENARIO_LABELS_KO = {
    ScenarioId.IDLE: '대기',
    ScenarioId.EXHIBIT_CONTACT: '전시품 접촉',
    ScenarioId.BATTERY_HANDOFF: '배터리 부족 임무 인계',
    ScenarioId.NIGHT_INTRUDER: '야간 침입자 감지',
    ScenarioId.EXHIBIT_LOSS: '전시품 분실',
    ScenarioId.FIRE_RESPONSE: '화재 의심 대응',
}


class TaskManagerNode(Node):
    """Subscribe to vision & Gen.G sensors, manage patrol tasks, command actuators."""

    def __init__(self) -> None:
        super().__init__('task_manager')

        self.declare_parameter('fire_temp_threshold_c', 40.0)
        self.declare_parameter('battery_low_threshold_pct', 20.0)
        self.declare_parameter('night_mode', False)
        self.declare_parameter('task_eval_period_sec', 0.5)
        self.declare_parameter('vision_timeout_sec', 5.0)
        self.declare_parameter('state_topic', '/museum/task/state')
        self.declare_parameter('command_topic', '/museum/task/command')

        self.fire_temp_threshold = (
            self.get_parameter('fire_temp_threshold_c').get_parameter_value().double_value
        )
        self.battery_low_threshold = (
            self.get_parameter('battery_low_threshold_pct').get_parameter_value().double_value
        )
        self.night_mode = (
            self.get_parameter('night_mode').get_parameter_value().bool_value
        )
        eval_period = (
            self.get_parameter('task_eval_period_sec').get_parameter_value().double_value
        )
        self.vision_timeout_sec = (
            self.get_parameter('vision_timeout_sec').get_parameter_value().double_value
        )
        state_topic = (
            self.get_parameter('state_topic').get_parameter_value().string_value
        )
        command_topic = (
            self.get_parameter('command_topic').get_parameter_value().string_value
        )

        self._yolo_status: str = ''
        self._yolo_fire: bool = False
        self._yolo_smoke: bool = False
        self._yolo_person: bool = False
        self._pir_active: bool = False
        self._temperature_c: float = 0.0
        self._battery_pct: float = 100.0
        self._last_image_time: Optional[float] = None
        self._vision_alive: bool = False

        self._forced_scenario: Optional[ScenarioId] = None
        self._exhibit_loss_flag: bool = False
        self._active_scenario: ScenarioId = ScenarioId.IDLE
        self._pump_on: bool = False
        self._laser_on: bool = False

        self.create_subscription(String, '/detect/status', self._detect_status_cb, 10)
        self.create_subscription(Image, '/detect/image_raw', self._detect_image_cb, 10)
        self.create_subscription(Bool, '/geng/sensor/pir', self._pir_cb, 10)
        self.create_subscription(Float32, '/geng/sensor/temperature', self._temperature_cb, 10)
        self.create_subscription(Float32, '/museum/battery/level', self._battery_cb, 10)
        self.create_subscription(MuseumCommand, command_topic, self._command_cb, 10)

        self.pump_pub = self.create_publisher(Bool, '/geng/control/pump', 10)
        self.laser_pub = self.create_publisher(Bool, '/geng/control/laser', 10)
        self.state_pub = self.create_publisher(MuseumState, state_topic, 10)

        self.create_timer(eval_period, self._evaluate_and_publish)

        self.get_logger().info(
            f'Task manager ready — publishing MuseumState to {state_topic}'
        )

    def _detect_status_cb(self, msg: String) -> None:
        self._yolo_status = msg.data
        self._yolo_fire = ('화재' in msg.data) or ('불꽃' in msg.data) or ('fire' in msg.data.lower())
        self._yolo_smoke = ('연기' in msg.data) or ('smoke' in msg.data.lower())
        self._yolo_person = ('사람' in msg.data) or ('person' in msg.data.lower())

    def _detect_image_cb(self, _msg: Image) -> None:
        self._last_image_time = time.monotonic()
        self._vision_alive = True

    def _pir_cb(self, msg: Bool) -> None:
        self._pir_active = msg.data

    def _temperature_cb(self, msg: Float32) -> None:
        self._temperature_c = msg.data

    def _battery_cb(self, msg: Float32) -> None:
        self._battery_pct = msg.data

    def _command_cb(self, msg: MuseumCommand) -> None:
        """Handle external commands from Main Server or Unity."""
        command_type = msg.command_type

        if command_type == 'exhibit_loss':
            self._exhibit_loss_flag = msg.active
            self.get_logger().info(f'Exhibit loss command: active={msg.active}')
        elif command_type == 'set_night_mode':
            self.night_mode = msg.night_mode
            self.get_logger().info(f'Night mode set to {self.night_mode}')
        elif command_type == 'force_scenario':
            try:
                self._forced_scenario = ScenarioId(msg.scenario_id)
            except ValueError:
                self.get_logger().warning(f'Unknown forced task scenario: {msg.scenario_id!r}')
                return
            self.get_logger().info(f'Task forced to {self._forced_scenario.value}')
        elif command_type == 'clear_force':
            self._forced_scenario = None
            self._exhibit_loss_flag = False
            self.get_logger().info('Forced task and flags cleared')
        else:
            self.get_logger().debug(f'Unhandled command_type: {command_type!r}')

    def _check_vision_health(self) -> None:
        if self._last_image_time is None:
            self._vision_alive = False
            return
        elapsed = time.monotonic() - self._last_image_time
        self._vision_alive = elapsed <= self.vision_timeout_sec

    def _evaluate_candidates(self) -> Dict[ScenarioId, str]:
        candidates: Dict[ScenarioId, str] = {}

        fire_by_temp = self._temperature_c >= self.fire_temp_threshold
        fire_by_vision = self._yolo_fire or self._yolo_smoke
        if fire_by_vision or fire_by_temp:
            parts = []
            if self._yolo_fire:
                parts.append('불꽃 감지')
            if self._yolo_smoke:
                parts.append('연기 감지')
            if fire_by_temp:
                parts.append(
                    f'온도 {self._temperature_c:.1f}°C (임계 {self.fire_temp_threshold:.1f}°C)'
                )
            candidates[ScenarioId.FIRE_RESPONSE] = '화재 의심 — ' + ', '.join(parts)

        if self.night_mode and (self._pir_active or self._yolo_person):
            parts = []
            if self._pir_active:
                parts.append('PIR 침입 감지')
            if self._yolo_person:
                parts.append('사람 감지')
            candidates[ScenarioId.NIGHT_INTRUDER] = '야간 침입 — ' + ', '.join(parts)

        if self._exhibit_loss_flag:
            candidates[ScenarioId.EXHIBIT_LOSS] = '전시품 분실 신고 수신'

        if not self.night_mode and self._yolo_person:
            candidates[ScenarioId.EXHIBIT_CONTACT] = '개장 중 사람 감지 — 전시품 접촉 의심'

        if self._battery_pct <= self.battery_low_threshold:
            candidates[ScenarioId.BATTERY_HANDOFF] = (
                f'배터리 {self._battery_pct:.1f}% — Gen.G 출동로봇 임무 인계 필요'
            )

        return candidates

    def _select_scenario(self, candidates: Dict[ScenarioId, str]) -> tuple[ScenarioId, str]:
        if self._forced_scenario is not None:
            message = candidates.get(
                self._forced_scenario,
                f'외부 강제 임무: {SCENARIO_LABELS_KO[self._forced_scenario]}',
            )
            return self._forced_scenario, message

        if not candidates:
            return ScenarioId.IDLE, '정상 순찰 중'

        best = max(candidates, key=lambda sid: SCENARIO_PRIORITY[sid])
        return best, candidates[best]

    def _apply_actuator_policy(self, scenario: ScenarioId) -> None:
        if scenario == ScenarioId.FIRE_RESPONSE:
            self._pump_on = True
            self._laser_on = False
        elif scenario == ScenarioId.NIGHT_INTRUDER:
            self._pump_on = False
            self._laser_on = True
        else:
            self._pump_on = False
            self._laser_on = False

    def _publish_actuators(self) -> None:
        pump_msg = Bool()
        pump_msg.data = self._pump_on
        self.pump_pub.publish(pump_msg)

        laser_msg = Bool()
        laser_msg.data = self._laser_on
        self.laser_pub.publish(laser_msg)

    def _build_state_msg(
        self,
        scenario: ScenarioId,
        message: str,
        status: str,
    ) -> MuseumState:
        state = MuseumState()
        state.scenario_id = scenario.value
        state.scenario_label = SCENARIO_LABELS_KO[scenario]
        state.status = status
        state.message = message
        state.fire_detected = self._yolo_fire
        state.smoke_detected = self._yolo_smoke
        state.person_detected = self._yolo_person
        state.yolo_status_raw = self._yolo_status
        state.pir_active = self._pir_active
        state.temperature_c = float(self._temperature_c)
        state.vision_alive = self._vision_alive
        state.night_mode = self.night_mode
        state.battery_pct = float(self._battery_pct)
        state.pump_on = self._pump_on
        state.laser_on = self._laser_on
        state.timestamp = time.time()
        return state

    def _evaluate_and_publish(self) -> None:
        self._check_vision_health()
        candidates = self._evaluate_candidates()
        scenario, message = self._select_scenario(candidates)

        if scenario != self._active_scenario:
            self.get_logger().warn(
                f'[임무 전환] {SCENARIO_LABELS_KO[self._active_scenario]} '
                f'→ {SCENARIO_LABELS_KO[scenario]} | {message}'
            )
            self._active_scenario = scenario

        self._apply_actuator_policy(scenario)
        self._publish_actuators()

        status = 'active' if scenario != ScenarioId.IDLE else 'idle'
        self.state_pub.publish(self._build_state_msg(scenario, message, status))

        if scenario != ScenarioId.IDLE:
            self.get_logger().info(
                f'[{SCENARIO_LABELS_KO[scenario]}] {message} | '
                f'pump={self._pump_on}, laser={self._laser_on}'
            )


def main(args=None) -> None:
    rclpy.init(args=args)
    node = TaskManagerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
