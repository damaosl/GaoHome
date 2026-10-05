/**
 * 高岛的眼睛 — 一键代理（系统集成，P1）
 *
 * Windows 平台：设置/读取「系统代理（WinINET）」与「用户级环境变量代理」。
 * - 系统代理：写 HKCU\...\Internet Settings，并用 wininet 通知浏览器/系统即时生效
 * - 环境变量：写 HKCU\Environment（HTTP_PROXY/HTTPS_PROXY），广播 WM_SETTINGCHANGE
 *   使新开的命令行进程生效
 */
import { execFile } from 'node:child_process';

export interface ProxyTargetStatus {
  enabled: boolean;
  server: string;
}

const REG_WININET = 'HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings';
const REG_ENV = 'HKCU\\Environment';

function sh(cmd: string, args: string[]): Promise<{ ok: boolean; stdout: string; stderr: string }> {
  return new Promise((resolve) => {
    execFile(cmd, args, { windowsHide: true, encoding: 'utf8' }, (err, stdout, stderr) => {
      resolve({ ok: !err, stdout: String(stdout ?? ''), stderr: String(stderr ?? '') });
    });
  });
}

async function runPs(script: string): Promise<void> {
  await sh('powershell', ['-NoProfile', '-NonInteractive', '-Command', script]);
}

/** 通知系统代理变更生效（wininet InternetSetOption） */
async function notifySystemProxy(): Promise<void> {
  await runPs(
    `$sig=@'
using System;using System.Runtime.InteropServices;
public class WI{[DllImport("wininet.dll")]public static extern bool InternetSetOption(IntPtr h,int o,IntPtr b,int l);}
'@; Add-Type -TypeDefinition $sig; [WI]::InternetSetOption([IntPtr]::Zero,39,[IntPtr]::Zero,0)|Out-Null; [WI]::InternetSetOption([IntPtr]::Zero,37,[IntPtr]::Zero,0)|Out-Null;`,
  );
}

/** 广播环境变量变更（WM_SETTINGCHANGE = 0x1A, "Environment"） */
async function notifyEnv(): Promise<void> {
  await runPs(
    `$sig=@'
using System;using System.Runtime.InteropServices;
public class EB{[DllImport("user32.dll",SetLastError=true)]public static extern IntPtr SendMessageTimeout(IntPtr h,uint m,UIntPtr w,string l,uint f,uint t,out UIntPtr r);}
'@; Add-Type -TypeDefinition $sig; $r=[UIntPtr]::Zero; [EB]::SendMessageTimeout([IntPtr]0xffff,0x1A,[UIntPtr]::Zero,'Environment',2,5000,[ref]$r)|Out-Null;`,
  );
}

export async function setSystemProxy(enable: boolean, host: string, port: number): Promise<void> {
  const server = `${host}:${port}`;
  if (enable) {
    await sh('reg', ['add', REG_WININET, '/v', 'ProxyEnable', '/t', 'REG_DWORD', '/d', '1', '/f']);
    await sh('reg', ['add', REG_WININET, '/v', 'ProxyServer', '/t', 'REG_SZ', '/d', server, '/f']);
    // 本机/回环直连，避免控制台自身被代理、产生回环与噪声
    await sh('reg', ['add', REG_WININET, '/v', 'ProxyOverride', '/t', 'REG_SZ', '/d', '<local>;localhost;127.0.0.1', '/f']);
  } else {
    await sh('reg', ['add', REG_WININET, '/v', 'ProxyEnable', '/t', 'REG_DWORD', '/d', '0', '/f']);
  }
  await notifySystemProxy();
}

export async function getSystemProxy(): Promise<ProxyTargetStatus> {
  const e = await sh('reg', ['query', REG_WININET, '/v', 'ProxyEnable']);
  const m = e.stdout.match(/ProxyEnable\s+REG_DWORD\s+(0x[0-9a-fA-F]+)/);
  const enabled = !!m && m[1].toLowerCase() === '0x1';
  const s = await sh('reg', ['query', REG_WININET, '/v', 'ProxyServer']);
  const sm = s.stdout.match(/ProxyServer\s+REG_SZ\s+(.+)/);
  return { enabled, server: sm ? sm[1].trim() : '' };
}

export async function setEnvProxy(enable: boolean, host: string, port: number): Promise<void> {
  const server = `http://${host}:${port}`;
  if (enable) {
    await sh('reg', ['add', REG_ENV, '/v', 'HTTP_PROXY', '/t', 'REG_SZ', '/d', server, '/f']);
    await sh('reg', ['add', REG_ENV, '/v', 'HTTPS_PROXY', '/t', 'REG_SZ', '/d', server, '/f']);
    await sh('reg', ['add', REG_ENV, '/v', 'NO_PROXY', '/t', 'REG_SZ', '/d', 'localhost,127.0.0.1', '/f']);
  } else {
    await sh('reg', ['delete', REG_ENV, '/v', 'HTTP_PROXY', '/f']);
    await sh('reg', ['delete', REG_ENV, '/v', 'HTTPS_PROXY', '/f']);
    await sh('reg', ['delete', REG_ENV, '/v', 'NO_PROXY', '/f']);
  }
  await notifyEnv();
}

export async function getEnvProxy(): Promise<ProxyTargetStatus> {
  const h = await sh('reg', ['query', REG_ENV, '/v', 'HTTP_PROXY']);
  const m = h.stdout.match(/HTTP_PROXY\s+REG_SZ\s+(.+)/);
  return { enabled: h.ok && !!m, server: m ? m[1].trim() : '' };
}

export interface ProxyTargetDef {
  id: 'system' | 'env';
  name: string;
  desc: string;
}

export const PROXY_TARGETS: ProxyTargetDef[] = [
  { id: 'system', name: '系统代理', desc: 'Edge / Chrome 及多数走系统代理的应用' },
  { id: 'env', name: '命令行工具', desc: 'Node / npm / git / curl / pip 等（新开终端生效）' },
];

export interface ProxyOverview {
  host: string;
  port: number;
  targets: ProxyTargetDef[];
  status: { system: ProxyTargetStatus; env: ProxyTargetStatus };
}

export async function getProxyStatus(host: string, port: number): Promise<ProxyOverview> {
  const [system, env] = await Promise.all([getSystemProxy(), getEnvProxy()]);
  return { host, port, targets: PROXY_TARGETS, status: { system, env } };
}
