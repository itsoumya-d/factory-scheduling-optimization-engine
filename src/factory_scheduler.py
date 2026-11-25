"""Operations Research & Job-Shop Production Scheduling Optimization Engine.

Provides discrete manufacturing scheduling across specialized electronics assembly work centers,
sequence-dependent setup minimization, precedence constraint enforcement, and bottleneck identification.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class MachineType(str, Enum):
    SMT_PICK_PLACE = "SMT_PICK_PLACE"
    REFLOW_OVEN = "REFLOW_OVEN"
    AOI_INSPECTION = "AOI_INSPECTION"
    XRAY_TEST = "XRAY_TEST"


@dataclass(frozen=True)
class ProductionStep:
    step_id: str
    machine_type: MachineType
    duration_minutes: float
    setup_family: str = "standard"


@dataclass(frozen=True)
class ProductionOrder:
    order_id: str
    panel_count: int
    deadline_minutes: float
    steps: List[ProductionStep]
    priority: int = 1  # 1 = normal, >1 = high priority


@dataclass(frozen=True)
class ScheduledTask:
    order_id: str
    step_id: str
    machine_id: str
    machine_type: MachineType
    start_time: float
    end_time: float
    setup_duration: float


@dataclass
class MachineState:
    machine_id: str
    machine_type: MachineType
    available_at: float = 0.0
    current_setup_family: str = "initial"
    total_processing_time: float = 0.0
    total_setup_time: float = 0.0


@dataclass(frozen=True)
class ScheduleSummary:
    makespan_minutes: float
    total_orders_scheduled: int
    on_time_delivery_rate: float
    bottleneck_machine_id: str
    machine_utilization: Dict[str, float]
    tasks: List[ScheduledTask] = field(default_factory=list)


class FactorySchedulingEngine:
    """Schedules multi-stage job-shop production orders across factory machinery."""

    def __init__(self, default_changeover_minutes: float = 15.0):
        self.changeover_penalty = default_changeover_minutes
        self._machines: Dict[str, MachineState] = {}

    def register_machine(self, machine_id: str, machine_type: MachineType) -> None:
        self._machines[machine_id] = MachineState(machine_id=machine_id, machine_type=machine_type)

    def get_machines_by_type(self, machine_type: MachineType) -> List[MachineState]:
        return [m for m in self._machines.values() if m.machine_type == machine_type]

    def schedule_orders(self, orders: List[ProductionOrder]) -> ScheduleSummary:
        """Schedules orders to minimize makespan while satisfying routing and precedence constraints."""
        if not orders:
            return ScheduleSummary(
                makespan_minutes=0.0,
                total_orders_scheduled=0,
                on_time_delivery_rate=1.0,
                bottleneck_machine_id="",
                machine_utilization={},
                tasks=[],
            )

        # Reset machine availability
        for m in self._machines.values():
            m.available_at = 0.0
            m.current_setup_family = "initial"
            m.total_processing_time = 0.0
            m.total_setup_time = 0.0

        # Sort orders by Priority DESC, then Deadline ASC (Earliest Due Date)
        sorted_orders = sorted(orders, key=lambda o: (-o.priority, o.deadline_minutes))

        order_completion_times: Dict[str, float] = {}
        order_step_completion: Dict[str, float] = {o.order_id: 0.0 for o in sorted_orders}
        all_tasks: List[ScheduledTask] = []

        for order in sorted_orders:
            for step in order.steps:
                eligible_machines = self.get_machines_by_type(step.machine_type)
                if not eligible_machines:
                    raise RuntimeError(f"No machines registered for step type {step.machine_type}")

                # Choose machine that finishes this step earliest
                best_machine: Optional[MachineState] = None
                earliest_finish = float("inf")
                best_setup = 0.0
                best_start = 0.0

                precedence_ready = order_step_completion[order.order_id]

                for machine in eligible_machines:
                    setup_time = 0.0
                    if (
                        machine.current_setup_family != "initial"
                        and machine.current_setup_family != step.setup_family
                    ):
                        setup_time = self.changeover_penalty

                    start_time = max(machine.available_at + setup_time, precedence_ready)
                    finish_time = start_time + step.duration_minutes

                    if finish_time < earliest_finish:
                        earliest_finish = finish_time
                        best_machine = machine
                        best_setup = setup_time
                        best_start = start_time

                assert best_machine is not None

                task = ScheduledTask(
                    order_id=order.order_id,
                    step_id=step.step_id,
                    machine_id=best_machine.machine_id,
                    machine_type=step.machine_type,
                    start_time=round(best_start, 2),
                    end_time=round(earliest_finish, 2),
                    setup_duration=round(best_setup, 2),
                )
                all_tasks.append(task)

                # Update machine state
                best_machine.available_at = earliest_finish
                best_machine.current_setup_family = step.setup_family
                best_machine.total_processing_time += step.duration_minutes
                best_machine.total_setup_time += best_setup

                # Update order precedence time
                order_step_completion[order.order_id] = earliest_finish

            order_completion_times[order.order_id] = order_step_completion[order.order_id]

        makespan = max(m.available_at for m in self._machines.values()) if self._machines else 0.0

        # Calculate on-time delivery rate
        on_time_count = sum(
            1 for o in sorted_orders if order_completion_times[o.order_id] <= o.deadline_minutes
        )
        on_time_rate = round(on_time_count / len(sorted_orders), 4)

        # Machine utilization and bottleneck identification
        utilization: Dict[str, float] = {}
        bottleneck_id = ""
        max_busy_time = -1.0

        for mid, m in self._machines.items():
            busy_time = m.total_processing_time + m.total_setup_time
            util = round(busy_time / makespan, 4) if makespan > 0 else 0.0
            utilization[mid] = util
            if busy_time > max_busy_time:
                max_busy_time = busy_time
                bottleneck_id = mid

        return ScheduleSummary(
            makespan_minutes=round(makespan, 2),
            total_orders_scheduled=len(sorted_orders),
            on_time_delivery_rate=on_time_rate,
            bottleneck_machine_id=bottleneck_id,
            machine_utilization=utilization,
            tasks=all_tasks,
        )
