// Research candidate, not a diagnostic or treatment recommendation.
// HbA1c must be supplied in NGSP percent (e.g. 6.0, not 0.06).
export const VERSION = 'hba1c-v0.1-unadjusted';
export const ANCHORS = Object.freeze([
  [4,100],[5,100],[5.5,90],[6,70],[6.5,50],[8,25],[10,10],
].map(Object.freeze));

export function scoreHba1c(value, {
  unit = '%', pregnancy = false, knownInterference = false,
} = {}) {
  const result = (score, status) => ({version:VERSION,value,unit,score,status});
  if(value == null) return result(null,'missing');
  if(typeof value !== 'number' || !Number.isFinite(value) || value <= 0)
    return result(null,'invalid_input');
  if(unit !== '%') return result(null,'unsupported_unit');
  if(pregnancy) return result(null,'pregnancy_outside_scope');
  if(knownInterference) return result(null,'interpretation_interference');
  // A coverage convention, NOT a claim that values below 4% are invalid.
  if(value < 4) return result(null,'below_model_coverage');
  if(value > 10) return result(10 * 2 ** (-(value-10)/2),'scored');
  for(let i=1;i<ANCHORS.length;i++) {
    const [leftX,leftY]=ANCHORS[i-1];
    const [rightX,rightY]=ANCHORS[i];
    if(value <= rightX) {
      const fraction=(value-leftX)/(rightX-leftX);
      return result(leftY+fraction*(rightY-leftY),'scored');
    }
  }
}
