"""Build a synthetic-only GitHub Pages demo from the local UI."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from jev_eval.web import audit

assets = ROOT / 'src/jev_eval/static'
target = ROOT / 'docs'
target.mkdir(exist_ok=True)
html = (assets / 'index.html').read_text()
html = html.replace('<meta name="jev-token" content="__TOKEN__">', '')
html = html.replace('href="/style.css"', 'href="./style.css"').replace('src="/app.js"', 'src="./app.js"').replace('href="/"', 'href="./"')
html = html.replace('Offline audit', 'Mock demo · synthetic data')
html = html.replace('LOCAL ENVIRONMENT', 'PUBLIC DEMO')
html = html.replace('Local evaluation', 'Synthetic evaluation')
html = html.replace('Local checks. Honest uncertainty.', 'Interactive mock. Synthetic traces only.')
html = html.replace('This UI runs offline guardrails. Semantic judgments require the CLI’s opt-in JEV mode; clean traces still need review.', 'Explore a fixed sample report. No backend or live JEV calls. Run jev-eval ui locally to evaluate your own traces.')
html = html.replace('NO API KEY NEEDED', 'NOT A LIVE EVALUATOR')
start = html.index('<label class="upload">')
end = html.index('</label>', start) + len('</label>')
html = html[:start] + '<div class="upload">◈ &nbsp; Synthetic sample pack<small>3 example traces · uploads disabled</small></div>' + html[end:]
html = html.replace('Editable JSON', 'Read-only sample').replace('id="traces"', 'id="traces" readonly')
html = html.replace('id="tools"', 'id="tools" readonly').replace('Comma-separated', 'Fixed demo policy')
html = html.replace('Run evaluation', 'Run demo evaluation')
html = html.replace('Your traces stay on this machine.', 'Synthetic demo only. No personal data is accepted.')
(target / 'index.html').write_text(html)
(target / 'style.css').write_text((assets / 'style.css').read_text())
js = (assets / 'app.js').read_text().split('async function run()')[0]
js += '''
async function run() {
  $('run').disabled = true;
  try {
    const response = await fetch('./demo-report.json');
    if (!response.ok) throw new Error('Sample report unavailable');
    report = await response.json();
    render();
    $('message').textContent = 'Simulated evaluation · fixed synthetic report · no JEV call.';
  } catch (_) {
    $('message').textContent = 'Unable to load demo. Refresh to try again.';
  } finally { $('run').disabled = false; }
}
$('run').onclick = run;
$('demo').onclick = () => { $('traces').value = JSON.stringify(demo, null, 2); run(); };
$('download').onclick = () => {
  const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], {type: 'application/json'}));
  const link = document.createElement('a'); link.href = url; link.download = 'jev-synthetic-demo.json'; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
};
$('traces').value = JSON.stringify(demo, null, 2);
run();
'''
(target / 'app.js').write_text(js)
traces = [json.loads(line) for line in (ROOT / 'examples/traces.jsonl').read_text().splitlines() if line.strip()]
report = audit({'traces': traces, 'allowed_tools': ['search_docs']})
report['demo'] = True
report['notice'] = 'Fixed synthetic demo. Not a live evaluation.'
(target / 'demo-report.json').write_text(json.dumps(report, indent=2))
(target / '.nojekyll').touch()
