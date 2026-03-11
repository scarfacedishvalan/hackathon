import sys, json
sys.path.insert(0, '.')
from app.orchestrators.bl_agent_orchestrator import run_agent

result = run_agent(
    thesis_name='alpha_tilt',
    goal='Maximise Sharpe ratio with sector diversification. No single asset above 20%. Run stress sweep on expected return assumptions.',
    max_steps=8
)

print('=== AUDIT COMPLETE ===')
print('audit_id:', result['audit_id'])
print('steps:', len(result['steps']))

print('\n=== BASE RESULT ===')
print(json.dumps(result['base_result_summary'], indent=2))

print('\n=== SCENARIOS RUN ===')
for k, v in result.get('scenarios_run', {}).items():
    warn = f"  !! {v.get('constraint_warning')}" if v.get('constraint_warning') else ''
    print(f'  [{k}]  sharpe={v.get("sharpe")}  weights={v.get("weights")}{warn}')

print('\n=== STEP TOOLS ===')
for s in result['steps']:
    tool = s.get('tool', s.get('type', '?'))
    args_str = json.dumps(s.get('args', {}))[:160]
    warn = ''
    if isinstance(s.get('result'), dict) and s['result'].get('constraint_warning'):
        warn = '\n    !! CONSTRAINT WARNING: ' + s['result']['constraint_warning']
    print(f'  step={s["step"]}  tool={tool}')
    print(f'    args={args_str}{warn}')

print('\n=== SYNTHESIS ===')
syn = result.get('synthesis', {})
print('narrative:', syn.get('narrative', '')[:1500])
print('risk_flags:', syn.get('risk_flags'))
print('recommended_weights:', syn.get('recommended_weights'))

print('\n=== COST ===')
print(json.dumps(result.get('cost_breakdown'), indent=2))
