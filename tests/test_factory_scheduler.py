import unittest
from src.factory_scheduler import (
    FactorySchedulingEngine,
    MachineType,
    ProductionOrder,
    ProductionStep,
)


class TestFactorySchedulingEngine(unittest.TestCase):
    def setUp(self):
        self.engine = FactorySchedulingEngine(default_changeover_minutes=15.0)
        self.engine.register_machine("smt-01", MachineType.SMT_PICK_PLACE)
        self.engine.register_machine("reflow-01", MachineType.REFLOW_OVEN)
        self.engine.register_machine("aoi-01", MachineType.AOI_INSPECTION)

    def test_single_order_precedence_constraint(self):
        order = ProductionOrder(
            order_id="ORD-001",
            panel_count=50,
            deadline_minutes=120.0,
            steps=[
                ProductionStep("step-smt", MachineType.SMT_PICK_PLACE, 30.0, "family-a"),
                ProductionStep("step-reflow", MachineType.REFLOW_OVEN, 15.0, "family-a"),
                ProductionStep("step-aoi", MachineType.AOI_INSPECTION, 10.0, "family-a"),
            ],
        )

        summary = self.engine.schedule_orders([order])
        self.assertEqual(summary.total_orders_scheduled, 1)
        self.assertEqual(len(summary.tasks), 3)

        smt_task = summary.tasks[0]
        reflow_task = summary.tasks[1]
        aoi_task = summary.tasks[2]

        # Precedence check: reflow starts >= smt ends, aoi starts >= reflow ends
        self.assertEqual(smt_task.start_time, 0.0)
        self.assertEqual(smt_task.end_time, 30.0)
        self.assertGreaterEqual(reflow_task.start_time, smt_task.end_time)
        self.assertEqual(reflow_task.end_time, 45.0)
        self.assertGreaterEqual(aoi_task.start_time, reflow_task.end_time)
        self.assertEqual(aoi_task.end_time, 55.0)
        self.assertEqual(summary.makespan_minutes, 55.0)
        self.assertEqual(summary.on_time_delivery_rate, 1.0)

    def test_sequence_dependent_setup_penalty(self):
        # Two orders with different setup families on same SMT machine
        order1 = ProductionOrder(
            order_id="ORD-001",
            panel_count=10,
            deadline_minutes=100.0,
            steps=[ProductionStep("s1", MachineType.SMT_PICK_PLACE, 20.0, "lead_free")],
        )
        order2 = ProductionOrder(
            order_id="ORD-002",
            panel_count=10,
            deadline_minutes=100.0,
            steps=[ProductionStep("s2", MachineType.SMT_PICK_PLACE, 20.0, "leaded_alloy")],
        )

        summary = self.engine.schedule_orders([order1, order2])
        # Order 1: 0 to 20
        # Order 2: setup (15 min) + 20 min -> starts at 35, ends at 55
        self.assertEqual(summary.tasks[0].setup_duration, 0.0)
        self.assertEqual(summary.tasks[1].setup_duration, 15.0)
        self.assertEqual(summary.tasks[1].start_time, 35.0)
        self.assertEqual(summary.tasks[1].end_time, 55.0)
        self.assertEqual(summary.makespan_minutes, 55.0)

    def test_parallel_machine_load_balancing(self):
        # Register a second SMT machine
        self.engine.register_machine("smt-02", MachineType.SMT_PICK_PLACE)

        order1 = ProductionOrder(
            order_id="ORD-001",
            panel_count=20,
            deadline_minutes=60.0,
            steps=[ProductionStep("s1", MachineType.SMT_PICK_PLACE, 30.0, "std")],
        )
        order2 = ProductionOrder(
            order_id="ORD-002",
            panel_count=20,
            deadline_minutes=60.0,
            steps=[ProductionStep("s2", MachineType.SMT_PICK_PLACE, 30.0, "std")],
        )

        summary = self.engine.schedule_orders([order1, order2])
        machines_used = {t.machine_id for t in summary.tasks}
        self.assertEqual(machines_used, {"smt-01", "smt-02"})
        # Parallel execution means makespan is 30.0 rather than 60.0
        self.assertEqual(summary.makespan_minutes, 30.0)

    def test_priority_and_bottleneck_detection(self):
        # Order 1 (priority 1) vs Order 2 (priority 2)
        order_low = ProductionOrder(
            order_id="ORD-LOW",
            panel_count=10,
            deadline_minutes=200.0,
            steps=[ProductionStep("s1", MachineType.SMT_PICK_PLACE, 40.0, "std")],
            priority=1,
        )
        order_high = ProductionOrder(
            order_id="ORD-HIGH",
            panel_count=10,
            deadline_minutes=200.0,
            steps=[ProductionStep("s2", MachineType.SMT_PICK_PLACE, 20.0, "std")],
            priority=2,
        )

        summary = self.engine.schedule_orders([order_low, order_high])
        # High priority scheduled first
        self.assertEqual(summary.tasks[0].order_id, "ORD-HIGH")
        self.assertEqual(summary.tasks[1].order_id, "ORD-LOW")
        self.assertEqual(summary.bottleneck_machine_id, "smt-01")
        self.assertEqual(summary.machine_utilization["smt-01"], 1.0)


if __name__ == "__main__":
    unittest.main()
