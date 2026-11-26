// TOTP (RFC 6238, SHA-1, 6 dígitos, passo de 30 s) calculado no próprio teste, a partir do segredo que o
// criar_admin devolve na URI otpauth://. Só para o teste ponta a ponta real.
import { createHmac } from "node:crypto";

const ALFABETO = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";

export function base32(texto: string): Buffer {
  const limpo = texto.replace(/=+$/, "").toUpperCase();
  let bits = "";
  for (const ch of limpo) {
    const v = ALFABETO.indexOf(ch);
    if (v < 0) throw new Error("segredo TOTP inválido");
    bits += v.toString(2).padStart(5, "0");
  }
  const bytes: number[] = [];
  for (let i = 0; i + 8 <= bits.length; i += 8) bytes.push(parseInt(bits.slice(i, i + 8), 2));
  return Buffer.from(bytes);
}

export function codigoTotp(segredo: string, agoraMs = Date.now(), passoS = 30): string {
  const contador = Math.floor(agoraMs / 1000 / passoS);
  const msg = Buffer.alloc(8);
  msg.writeBigUInt64BE(BigInt(contador));
  const mac = createHmac("sha1", base32(segredo)).update(msg).digest();
  const deslocamento = mac[mac.length - 1]! & 0x0f;
  const numero = (mac.readUInt32BE(deslocamento) & 0x7fffffff) % 1_000_000;
  return String(numero).padStart(6, "0");
}
