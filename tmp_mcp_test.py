import json
import subprocess
import sys
import time

proc = subprocess.Popen(
    [sys.executable, '-m', 'drift', 'mcp', '--serve'],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
)

def send_msg(msg_dict):
    msg = json.dumps(msg_dict).encode('utf-8')
    header = f'Content-Length: {len(msg)}\r\n\r\n'.encode()
    proc.stdin.write(header + msg)
    proc.stdin.flush()

def read_msg(timeout=15):
    header = b''
    deadline = time.time() + timeout
    while time.time() < deadline:
        ch = proc.stdout.read(1)
        if not ch:
            break
        header += ch
        if header.endswith(b'\r\n\r\n'):
            break
    parts = header.split(b'Content-Length: ')
    if len(parts) < 2:
        # Check stderr
        stderr_data = proc.stderr.read1(4096) if hasattr(proc.stderr, 'read1') else b''
        sys.stderr.write('HEADER PARSE FAIL, stderr: ' + stderr_data.decode(errors='replace') + '\n')
        return None
    length = int(parts[1].split(b'\r\n')[0])
    return json.loads(proc.stdout.read(length))

# Initialize
send_msg({'jsonrpc':'2.0','id':1,'method':'initialize','params':{
    'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'test','version':'0'}
}})
resp = read_msg(timeout=10)
if not resp:
    # Check if server even started
    proc.stdin.close()
    _, err = proc.communicate(timeout=5)
    print('Server failed to start. STDERR:', err.decode(errors='replace')[:500], file=sys.stderr)
    sys.exit(1)

print('Init OK:', resp.get('result',{}).get('serverInfo',{}).get('name','?'))

# Send initialized notification (required by MCP spec)
send_msg({'jsonrpc':'2.0','method':'notifications/initialized','params':{}})
send_msg({'jsonrpc':'2.0','id':2,'method':'tools/call','params':{
    'name':'drift_scan',
    'arguments':{'path':'.','max_findings':3,'response_detail':'concise'}
}})
resp = read_msg(timeout=30)
if resp:
    content = resp.get('result',{}).get('content',[])
    for item in content:
        if item.get('type')=='text':
            text = item['text']
            s, e = text.find('{'), text.rfind('}')
            if s>=0:
                parsed = json.loads(text[s:e+1])
                print('SCAN KEYS:', list(parsed.keys()))
                findings = parsed.get('findings', [])
                print(f'FINDINGS COUNT: {len(findings)}')
                print(f'composite_score: {parsed.get("composite_score")}')
                print(f'score: {parsed.get("score")}')
                if findings:
                    f0 = findings[0]
                    print('FINDING[0] KEYS:', list(f0.keys()))
                    print('  signal_id:', f0.get('signal_id'))
                    print('  file:', f0.get('file'))
                    print('  severity:', f0.get('severity'))
                    print('  line:', f0.get('line'))
                    print('  reason:', str(f0.get('reason',''))[:80])
            else:
                print('RAW (no JSON):', text[:200])
else:
    print('SCAN response FAILED - timeout')

# drift_nudge
send_msg({'jsonrpc':'2.0','id':3,'method':'tools/call','params':{
    'name':'drift_nudge',
    'arguments':{'path':'.','changed_files':'src/drift/mcp_server.py','timeout_ms':1000}
}})
resp = read_msg(timeout=10)
if resp:
    content = resp.get('result',{}).get('content',[])
    for item in content:
        if item.get('type')=='text':
            text = item['text']
            s, e = text.find('{'), text.rfind('}')
            if s>=0:
                parsed = json.loads(text[s:e+1])
                print('NUDGE KEYS:', list(parsed.keys()))
                print('  direction:', parsed.get('direction'))
                print('  safe_to_commit:', parsed.get('safe_to_commit'))
                print('  revert_recommended:', parsed.get('revert_recommended'))
                print('  latency_exceeded:', parsed.get('latency_exceeded'))
            else:
                print('NUDGE RAW:', text[:200])

proc.kill()
print('DONE')
