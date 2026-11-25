# factory-scheduling-optimization-engine

Operations research and constraint optimization engine for high-mix, small-batch electronics manufacturing: models machine routing, setup changeovers, sequence-dependent setup times, and heuristic makespan minimization.

## Architecture & Guarantees

- **Job-Shop Machine Routing**: Schedules multi-stage electronics assembly orders across specialized work centers (Pick-and-Place, Reflow Oven, AOI Inspection).
- **Sequence-Dependent Setup Optimization**: Models component reel changeover costs and groups compatible production batches to minimize idle setup time.
- **Capacity & Bottleneck Detection**: Calculates machine utilization metrics and identifies bottleneck work centers across dynamic planning horizons.
- **Deadline-Aware Dispatch**: Prioritizes urgent production runs while satisfying machine non-overlap and precedence constraints.

## Run Tests Locally

```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```

## CI/CD

Automated GitHub Actions workflow runs unit tests and linting on every push and pull request.
