/**
 * 冒烟测试：验证匹配引擎 + 四种动作模式。
 * 运行：npm run smoke 或 npx tsx scripts/smoke.ts
 */
import { matchRules } from '../src/rules/matcher.js';
import { applyRequestAction, applyResponseAction } from '../src/proxy/apply.js';
import type { ProxyRequest, ProxyResponse, Rule } from '../src/types.js';

let failed = 0;
function check(name: string, cond: boolean, detail?: unknown) {
  if (cond) {
    console.log(`  ✓ ${name}`);
  } else {
    failed++;
    console.error(`  ✗ ${name}`, detail ?? '');
  }
}

const baseRule = (over: Partial<Rule>): Rule => ({
  id: 'r1',
  name: 'r1',
  enabled: true,
  match: { pattern: '', type: 'substring', methods: [], phase: 'response' },
  action: { mode: 'replace', status: 200, headers: {}, body: '' },
  ...over,
});

console.log('— 匹配引擎 —');
{
  const rules: Rule[] = [
    baseRule({ id: 'a', match: { pattern: 'api/user', type: 'substring', methods: [], phase: 'response' } }),
    baseRule({ id: 'b', match: { pattern: 'api/user', type: 'substring', methods: ['POST'], phase: 'response' } }),
    baseRule({ id: 'c', match: { pattern: '^https://x\\.com/.*$', type: 'regex', methods: [], phase: 'request' } }),
    baseRule({ id: 'd', enabled: false, match: { pattern: 'api/user', type: 'substring', methods: [], phase: 'response' } }),
  ];
  const hits = matchRules(rules, { url: 'https://x.com/api/user/1', method: 'GET', phase: 'response' });
  check('禁用规则不命中', hits.every((h) => h.id !== 'd'));
  check('方向过滤：request 规则不命中 response', hits.every((h) => h.id !== 'c'));
  check('方法过滤：POST 规则不命中 GET', hits.every((h) => h.id !== 'b'));
  check('substring 命中', hits.some((h) => h.id === 'a'));
  const reqHits = matchRules(rules, { url: 'https://x.com/whatever', method: 'GET', phase: 'request' });
  check('regex 命中请求方向', reqHits.some((h) => h.id === 'c'));
}

console.log('— 请求方向动作 —');
{
  const req: ProxyRequest = { method: 'GET', url: 'https://x.com/a', headers: {}, body: '' };
  const guide = applyRequestAction(baseRule({ action: { mode: 'guide', redirectTo: 'https://y.com/b' } }), req);
  check('guide → redirect', guide.kind === 'redirect' && guide.url === 'https://y.com/b', guide);
  const rep = applyRequestAction(baseRule({ action: { mode: 'replace', status: 418, headers: { 'x-fake': '1' }, body: 'teapot' } }), req);
  check('replace → respond', rep.kind === 'respond' && rep.response.status === 418 && rep.response.body === 'teapot', rep);
  const app = applyRequestAction(baseRule({ action: { mode: 'append', where: 'body', value: 'x' } }), req);
  check('append 在请求方向忽略', app.kind === 'passthrough', app);
}

console.log('— 响应方向动作 —');
const res = (body: string, ct = 'application/json'): ProxyResponse => ({
  status: 200, headers: { 'content-type': ct, 'content-length': String(body.length) }, body, contentType: ct, text: true,
});
{
  const req: ProxyRequest = { method: 'GET', url: 'https://x.com/a', headers: {}, body: '' };
  const guide = applyResponseAction(baseRule({ action: { mode: 'guide', redirectTo: 'https://z.com' } }), res('{}'), req);
  check('guide → 302 引导', guide.kind === 'replace' && guide.response.status === 302 && guide.response.headers.location === 'https://z.com', guide);
  const rep = applyResponseAction(baseRule({ action: { mode: 'replace', status: 200, headers: { 'content-type': 'application/json' }, body: '{"fake":1}' } }), res('{"real":1}'), req);
  check('replace → 截止更改', rep.kind === 'replace' && rep.response.body === '{"fake":1}', rep);
  const app = applyResponseAction(baseRule({ action: { mode: 'append', where: 'json', value: '{"extra":2}' } }), res('{"real":1}'), req);
  check('append json → 合并字段', app.response.body.includes('"real"') && app.response.body.includes('"extra": 2'), app.response.body);
  const appBody = applyResponseAction(baseRule({ action: { mode: 'append', where: 'body', value: ' END' } }), res('hello', 'text/plain'), req);
  check('append body → 文本拼接', appBody.response.body === 'hello END', appBody.response.body);
  const mod = applyResponseAction(baseRule({ action: { mode: 'modify', patches: [{ op: 'set', path: 'user.name', value: '"Bob"' }, { op: 'delete', path: 'secret' }] } }), res('{"user":{"name":"Alice"},"secret":"x"}'), req);
  check('modify set + delete', mod.response.body.includes('"Bob"') && !mod.response.body.includes('secret'), mod.response.body);
}

if (failed > 0) {
  console.error(`\n${failed} 项失败`);
  process.exit(1);
}
console.log('\n全部通过');
