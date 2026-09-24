/** Minimal reference client. Retains domain results, nulls, bounds and all notices. */
export async function scoreDomains(request, {baseUrl = '', fetchImpl = globalThis.fetch, signal} = {}) {
  const response = await fetchImpl(`${baseUrl}/api/v1/score`, {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(request), signal,
  });
  if (!response.ok) throw new Error(`Scoring request failed (HTTP ${response.status}).`);
  const result = await response.json();
  if (result.api_version !== '1.0' || !result.domains) throw new Error('Unsupported scoring response.');
  return result;
}

export function displayPoints(component) {
  // Zero is a real score. A missing score is not zero, and a bounded range is not an exact score.
  return component?.score == null ? '—' : (component.display_score ?? String(component.score));
}
