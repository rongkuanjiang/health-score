import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {scoreDomains, displayPoints} from './integration_client.mjs';
const fixture = name => JSON.parse(readFileSync(new URL(`./integration_examples/${name}.response.json`, import.meta.url)));
for (const name of ['worked', 'incomplete', 'age16', 'partial-error']) {
  const expected = fixture(name);
  const result = await scoreDomains({}, {fetchImpl: async () => ({ok: true, json: async () => expected})});
  assert.deepEqual(result, expected); // Preserve notices, processing errors, withheld values and provenance.
  assert.equal(result.overall_score, null);
}
assert.equal(displayPoints({score: null, display_score: null}), '—');
assert.equal(displayPoints({score: 0, display_score: '0.0'}), '0.0');
assert.equal(displayPoints({score: 0.001, display_score: '<0.1'}), '<0.1');
assert.equal(displayPoints({score: null, score_range: [75, 100]}), '—');
await assert.rejects(scoreDomains({}, {fetchImpl: async () => ({ok: false, status: 400})}), /HTTP 400/);
await assert.rejects(scoreDomains({}, {fetchImpl: async () => {throw new Error('offline');}}), /offline/);
await assert.rejects(scoreDomains({}, {fetchImpl: async () => ({ok: true, json: async () => ({api_version: '2.0'})})}), /Unsupported/);
console.log('Integration client checks passed.');
