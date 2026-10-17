import numpy as np

from app.checker import check
from app.replay import run_replay, simulate
from app.solver import effective_due, outage_windows, solve
from app.timeutil import hm
from helpers import constraint


def test_checked_running_operation_restarts_when_noise_crosses_future_outage(F):
    constraints = [constraint("c1", "machine_down", machine="M1", **{"from": "10:11", "until": "11:00"})]
    plan = solve(F, constraints, reroute=True, overtime=False)
    assert check(F, constraints, plan["schedule"])["valid"]
    sim, _ = simulate(plan["schedule"], effective_due(F, constraints), hm(F["now"]),
                      outage_windows(F, constraints), n=500, seed=7, repair_extra_max=0)
    _, starts, ends = next(row for row in sim if row[0]["job"] == "J6" and row[0]["op"] == 1)
    assert (starts == hm("09:00")).all()  # observed history is not moved
    restarted = ends >= hm("11:00")
    assert restarted.sum() == 156
    assert (ends[~restarted] <= hm("10:11")).all()
    # Restart uses the full 70-minute operation, not just the lost remaining work.
    assert (ends[restarted] >= hm("11:00") + 70 * 0.9).all()


def small_plan():
    return [{"job": "J1", "op": 1, "machine": "M1", "start": "09:00", "end": "10:10"},
            {"job": "J1", "op": 2, "machine": "M2", "start": "10:10", "end": "10:20"}]


def test_restart_delay_propagates_to_next_operation():
    sim, _ = simulate(small_plan(), {"J1": hm("10:30")}, hm("10:00"),
                      {"M1": [(hm("10:11"), hm("11:00"))]}, n=500, seed=7, repair_extra_max=0)
    first, second = sim
    assert (second[1] >= first[2]).all()
    restarted = first[2] >= hm("11:00")
    assert restarted.any() and (second[1][restarted] >= hm("11:00") + 63).all()


def test_failure_timeline_exposes_interruption_and_full_restart():
    result = run_replay({"now": "10:00", "jobs": [{"id": "J1"}]}, small_plan(),
                        {"M1": [(hm("10:11"), hm("11:00"))]}, {"J1": hm("10:30")}, {"J1": 1},
                        {"samples": 500, "seed": 7, "repair_delay_max_min": 0})
    failure = result["failing_scenario"]
    running, successor = failure["timeline"]
    assert running["start"] == "09:00"
    assert running["segments"][0] == {"start": "09:00", "end": "10:11", "kind": "interrupted"}
    assert running["segments"][1]["start"] == "11:00"
    assert running["segments"][1]["kind"] == "restart"
    assert running["segments"][1]["end"] == running["end"]
    assert hm(successor["start"]) >= hm(running["end"])
    assert "restart" in result["assumptions"]["running_work"].lower()


def test_running_restart_can_be_interrupted_by_another_future_outage():
    result = run_replay({"now": "10:00", "jobs": [{"id": "J1"}]}, small_plan(),
                        {"M1": [(hm("10:11"), hm("11:00")), (hm("11:20"), hm("11:40"))]},
                        {"J1": hm("10:30")}, {"J1": 1},
                        {"samples": 500, "seed": 7, "repair_delay_max_min": 0})
    running = result["failing_scenario"]["timeline"][0]
    assert [(s["start"], s["end"]) for s in running["segments"][:-1]] == \
           [("09:00", "10:11"), ("11:00", "11:20")]
    assert running["segments"][-1]["start"] == "11:40"
    assert hm(running["segments"][-1]["end"]) >= hm("11:40") + 63


def test_future_outage_does_not_change_zero_noise_or_finished_history():
    schedule = [{"job": "J2", "op": 1, "machine": "M1", "start": "08:00", "end": "09:00"}] + small_plan()
    sim, _ = simulate(schedule, {"J1": hm("10:30"), "J2": hm("09:00")}, hm("10:00"),
                      {"M1": [(hm("10:11"), hm("11:00"))]}, n=50, spread=(1, 1), repair_extra_max=0)
    for row, starts, ends in sim:
        np.testing.assert_array_equal(starts, hm(row["start"]))
        np.testing.assert_array_equal(ends, hm(row["end"]))


def test_overlapping_sampled_repairs_do_not_invent_processing_between_them():
    result = run_replay({"now": "10:00", "jobs": [{"id": "J1"}]}, small_plan(),
                        {"M1": [(hm("10:11"), hm("11:00")), (hm("11:05"), hm("11:10"))]},
                        {"J1": hm("10:30")}, {"J1": 1},
                        {"samples": 500, "seed": 7, "repair_delay_max_min": 90})
    segments = result["failing_scenario"]["timeline"][0]["segments"]
    assert segments[0]["start"] == "09:00" and segments[0]["end"] == "10:11"
    for piece in segments:
        assert hm(piece["end"]) >= hm(piece["start"])
        for start, end in (("10:11", "11:00"), ("11:05", "11:10")):
            assert hm(piece["end"]) <= hm(start) or hm(piece["start"]) >= hm(end)
