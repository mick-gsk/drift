import subprocess, json, sys, time, threading

proc = subprocess.Popen(
    [sys.executable, '-m', 'drift', 'mcp', '--serve'],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
)

results = []
stderr_buf = []

def read_stderr():
    for line in proc.stderr:
        stderr_buf.append(line.decode(errors='replace').rstrip())

def read_stdout():
    for line in proc.stdout:
        line = line.decode(errors='replace').rstrip()
        if line:
            results.append(line)

t_err = threading.Thread(target=read_stderr, daemon=True)
t_out = threading.Thread(target=read_stdout, daemon=True)
t_err.start()
t_out.start()

def send(msg):
    proc.stdin.write((json.dumps(msg) + '\n').encode())
    proc.stdin.flush()

def wait_for_id(id_, timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        for line in list(results):
            try:
                obj = json.loads(line)
                if obj.get('id') == id_:
                    return obj
            except:
                pass
        time.sleep(0.1)
    return None

# Initialize (newline-delimited JSON)
send({'jsonrpc':'2.0','id':1,'method':'initialize','params':{
    'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'test','version':'0'}
}})

resp = wait_for_id(1, timeout=8)
if not resp:
    proc.kill()
    print('INIT FAILED. Stderr:', '\n'.join(stderr_buf[:20]))
    sys.exit(1)

print('Init OK')
# Initialized notification
send({'jsonrpc':'2.0','method':'notifications/initialized','params':{}})

# drift_scan
send({'jsonrpc':'2.0','id':2,'method':'tools/call','params':{
    'name':'drift_scan',
    'arguments':{'path':'.','max_findings':3,'response_detail':'concise'}
}})
resp = wait_for_id(2, timeout=30)
if resp:
    content = resp.get('result',{}).get('content',[])
    for item in content:
        if item.get('type')=='text':
            text = item['text']
            s, e = text.find('{'), text.rfind('}')
            if s >= 0:
                parsed = json.loads(text[s:e+1])
                print('SCAN KEYS:', list(parsed.keys()))
                findings = parsed.get('findings',[])
                print(f'FINDINGS: {len(findings)}')
                print(f'composite_score: {parsed.get("composite_score")}')
                if findings:
                    f0 = findings[0]
                    print('FINDING KEYS:', list(f0.keys()))
                    print('  signal_id:', f0.get('signal_id'))
                    print('  file:', f0.get('file'))
                    print('  severity:', f0.get('severity'))
                    print('  line:', f0.get('line'))
            else:
                print('SCAN RAW:', text[:300])
else:
    print('SCAN TIMEOUT. Stderr:', '\n'.join(stderr_buf[:10]))

# drift_nudge
send({'jsonrpc':'2.0','id':3,'method':'tools/call','params':{
    'name':'drift_nudge',
    'arguments':{'path':'.','changed_files':'src/drift/mcp_server.py','timeout_ms':1000}
}})
resp = wait_for_id(3, timeout=10)
if resp:
    content = resp.get('result',{}).get('content',[])
    for item in content:
        if item.get('type')=='text':
            text = item['text']
            s, e = text.find('{'), text.rfind('}')
            if s >= 0:
                parsed = json.loads(text[s:e+1])
                print('NUDGE KEYS:', list(parsed.keys()))
                print('  direction:', parsed.get('direction'))
                print('  safe_to_commit:', parsed.get('safe_to_commit'))
                print('  latency_exceeded:', parsed.get('latency_exceeded'))
else:
    print('NUDGE TIMEOUT')

proc.kill()
print('\nDONE')
if stderr_buf:
    print('Server stderr (last 5):', '\n'.join(stderr_buf[-5:]))
