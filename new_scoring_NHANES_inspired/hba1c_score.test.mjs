import {test} from 'node:test';
import assert from 'node:assert/strict';
import {scoreHba1c} from './hba1c_score.mjs';
test('anchor values, interpolation and high tail',()=>{
  for(const [x,y] of [[4,100],[4.5,100],[5,100],[5.5,90],[5.75,80],[6,70],[6.25,60],[6.5,50],[8,25],[9,17.5],[10,10],[12,5],[14,2.5]])
    assert.equal(scoreHba1c(x).score,y);
});
test('missing, invalid, unsupported and out-of-scope values never become scores',()=>{
  for(const x of [null,undefined])assert.equal(scoreHba1c(x).status,'missing');
  for(const x of [NaN,Infinity,-1,0,'6'])assert.equal(scoreHba1c(x).status,'invalid_input');
  assert.equal(scoreHba1c(3.9).status,'below_model_coverage');
  assert.equal(scoreHba1c(42,{unit:'mmol/mol'}).status,'unsupported_unit');
  assert.equal(scoreHba1c(6,{pregnancy:true}).score,null);
  assert.equal(scoreHba1c(6,{knownInterference:true}).score,null);
});
test('bounded, nonincreasing and continuous across scored anchor boundaries',()=>{
  let previous=100;
  for(let i=400;i<=2000;i++){
    const s=scoreHba1c(i/100).score;
    assert(s>=0&&s<=100&&s<=previous+1e-10);previous=s;
  }
  for(const x of [5,5.5,6,6.5,8,10])
    assert(Math.abs(scoreHba1c(x-1e-7).score-scoreHba1c(x+1e-7).score)<1e-4);
});
