/**
 * 高岛的眼睛 — 配置与 CLI 参数（P2）
 */

export interface Config {
  proxyPort: number;
  apiPort: number;
  insecure: boolean;
  version: string;
}

export const VERSION = '0.1.0';

const HELP = `高岛的眼睛 — 极简假反馈拦截工具

用法:
  高岛的眼睛 [选项]

选项:
  -p, --proxy-port <port>   代理端口（应用/接口/插件指向它），默认 8888
  -a, --api-port <port>     控制台/UI 端口，默认 8787
  -k, --insecure            忽略上游 HTTPS 证书校验（自签名上游用）
  -h, --help                显示帮助

环境变量:
  MOCKFEED_DATA             规则持久化文件路径（默认 ./data/rules.json）
`;

export function parseArgs(argv: string[]): Config {
  const args = argv.slice(2);
  let proxyPort = 8888;
  let apiPort = 8787;
  let insecure = false;

  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a === '--proxy-port' || a === '-p') {
      proxyPort = Number(args[++i]) || proxyPort;
    } else if (a === '--api-port' || a === '-a') {
      apiPort = Number(args[++i]) || apiPort;
    } else if (a === '--insecure' || a === '-k') {
      insecure = true;
    } else if (a === '--help' || a === '-h') {
      console.log(HELP);
      process.exit(0);
    }
  }

  return { proxyPort, apiPort, insecure, version: VERSION };
}
