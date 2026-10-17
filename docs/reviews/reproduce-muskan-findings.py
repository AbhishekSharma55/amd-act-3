"""Offline reproductions for the pinned PR review; no AMD requests or file writes.

Run from a checkout containing PRs 22-26 with backend requirements-dev installed.
This script reports the observed behavior; it is evidence, not a passing test suite.
"""
import json
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from fastapi.testclient import TestClient
from app import runstore, state
from app.fixture import get_fixture
from app.main import app
from app import routes_extract
from app.replay import simulate
from app.solver import solve, outage_windows, effective_due
from app.checker import check
from app.timeutil import hm
from app.validate import validate_constraints

def fake(proposals):
    def extract(message, fixture):
        return {'constraints': proposals, 'trace': {
            'provider': 'Stub for review only', 'model': 'stub', 'host': 'local',
            'latency_ms': 0, 'attempts': 1, 'usage': None,
            'raw_output': '{}', 'fallback_used': False, 'mode': 'test'}}
    routes_extract.extract_amd = extract
    routes_extract.limiter._hits.clear()

client = TestClient(app)
runstore.clear()
state.approvals._runs.clear()

message = 'Mill 4 is down until 14:00. J7 must ship at 12:00.'
fake([
    {'type':'machine_down', 'params':{'machine':'Mill 4','until':'14:00'},
     'source_span':'Mill 4 is down until 14:00'},
    {'type':'due_date', 'params':{'job':'J7','time':'12:00'},
     'source_span':'J7 must ship at 12:00'}])
draft = client.post('/api/extract',json={'message':message}).json()
reviewed = deepcopy(draft['constraints'])
reviewed[0]['params']['machine'] = 'M1'
rv = client.post('/api/constraints/revalidate',json={'run_id':draft['run_id'],'constraints':reviewed}).json()
res = client.post('/api/solve',json={'run_id':draft['run_id'],'constraints':rv['constraints']})
print('REVIEW_LOST', json.dumps({
    'initial_date':draft['constraints'][1],
    'revalidated_date':rv['constraints'][1],
    'solve_status':res.status_code,
    'J7_lateness':[j for a in res.json()['alternatives'] for j in a['kpis']['late_jobs'] if j['job']=='J7']}))

F = get_fixture()
message = 'M1 is down from 10:11 until 11:00.'
cs = validate_constraints(message, [{'type':'machine_down',
    'params':{'machine':'M1','from':'10:11','until':'11:00'},
    'source_span':message}], F)
plan = solve(F,cs,reroute=True,overtime=False)
sim,_ = simulate(plan['schedule'],effective_due(F,cs),hm(F['now']),outage_windows(F,cs),n=500,seed=7,repair_extra_max=0)
row,s,e = next(x for x in sim if x[0]['job']=='J6' and x[0]['op']==1)
hit = (s < hm('11:00')) & (e > hm('10:11'))
print('RUNNING_OUTAGE', json.dumps({'solver_status':plan['status'],
    'checker':check(F,cs,plan['schedule']), 'running_op':row,
    'outage':'M1 10:11-11:00','overlap_samples':int(hit.sum()),
    'total':len(hit),'latest_end_min':float(e.max())}))
