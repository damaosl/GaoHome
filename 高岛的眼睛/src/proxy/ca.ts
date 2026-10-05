/**
 * 高岛的眼睛 — CA 证书与按域名签发证书（P0）
 *
 * 首次运行时生成一个本地根 CA（node-forge），HTTPS MITM 时
 * 为每个域名动态签发叶子证书。用户需信任 .certs/ca.crt.pem。
 */
import forge from 'node-forge';
import fs from 'node:fs';
import path from 'node:path';
import tls from 'node:tls';

export const CERTS_DIR = path.join(process.cwd(), '.certs');
const CA_KEY_PATH = path.join(CERTS_DIR, 'ca.key.pem');
const CA_CERT_PATH = path.join(CERTS_DIR, 'ca.crt.pem');

let caKey: forge.pki.rsa.PrivateKey;
let caCert: forge.pki.Certificate;

export function ensureCA(): { loaded: boolean; generated: boolean } {
  fs.mkdirSync(CERTS_DIR, { recursive: true });

  if (fs.existsSync(CA_KEY_PATH) && fs.existsSync(CA_CERT_PATH)) {
    try {
      caKey = forge.pki.privateKeyFromPem(fs.readFileSync(CA_KEY_PATH, 'utf8'));
      caCert = forge.pki.certificateFromPem(fs.readFileSync(CA_CERT_PATH, 'utf8'));
      return { loaded: true, generated: false };
    } catch {
      // 损坏则重新生成
    }
  }

  const keys = forge.pki.rsa.generateKeyPair(2048);
  caKey = keys.privateKey;

  caCert = forge.pki.createCertificate();
  caCert.publicKey = keys.publicKey;
  caCert.serialNumber = '01';
  caCert.validity.notBefore = new Date();
  caCert.validity.notAfter = new Date();
  caCert.validity.notAfter.setFullYear(caCert.validity.notAfter.getFullYear() + 10);

  const attrs: forge.pki.CertificateField[] = [
    { name: 'commonName', value: '高岛的眼睛 Local CA' },
    { name: 'organizationName', value: '高岛的眼睛' },
    { name: 'countryName', value: 'CN' },
  ];
  caCert.setSubject(attrs);
  caCert.setIssuer(attrs);
  caCert.setExtensions([
    { name: 'basicConstraints', cA: true },
    { name: 'keyUsage', keyCertSign: true, digitalSignature: true, cRLSign: true },
  ]);
  caCert.sign(caKey, forge.md.sha256.create());

  fs.writeFileSync(CA_KEY_PATH, forge.pki.privateKeyToPem(caKey));
  fs.writeFileSync(CA_CERT_PATH, forge.pki.certificateToPem(caCert));
  return { loaded: false, generated: true };
}

export function getCACertPath(): string {
  return CA_CERT_PATH;
}

const hostCertCache = new Map<string, { key: string; cert: string }>();

export function getHostCert(hostname: string): { key: string; cert: string } {
  if (hostCertCache.has(hostname)) return hostCertCache.get(hostname)!;

  const keys = forge.pki.rsa.generateKeyPair(2048);
  const cert = forge.pki.createCertificate();

  cert.publicKey = keys.publicKey;
  cert.serialNumber = Date.now().toString(16);
  cert.validity.notBefore = new Date();
  cert.validity.notAfter = new Date();
  cert.validity.notAfter.setFullYear(cert.validity.notAfter.getFullYear() + 1);

  cert.setSubject([{ name: 'commonName', value: hostname }]);
  cert.setIssuer(caCert.subject.attributes);
  cert.setExtensions([
    { name: 'basicConstraints', cA: false },
    { name: 'keyUsage', digitalSignature: true, keyEncipherment: true },
    { name: 'subjectAltName', altNames: [{ type: 2, value: hostname }] },
  ]);
  cert.sign(caKey, forge.md.sha256.create());

  const result = {
    key: forge.pki.privateKeyToPem(keys.privateKey),
    cert: forge.pki.certificateToPem(cert),
  };
  hostCertCache.set(hostname, result);
  return result;
}

export function createSecureContext(hostname: string): tls.SecureContext {
  const c = getHostCert(hostname);
  return tls.createSecureContext({ key: c.key, cert: c.cert });
}
