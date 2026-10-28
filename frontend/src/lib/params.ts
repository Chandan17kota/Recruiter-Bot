/** A route id like "3" -> 3. Anything that isn't a positive integer -> null (rendered as not found). */
export function parseId(raw: string | undefined): number | null {
  if (!raw || !/^[1-9]\d{0,9}$/.test(raw)) return null;
  const n = Number(raw);
  return n <= 2_147_483_647 ? n : null;
}
