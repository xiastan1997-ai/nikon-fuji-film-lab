import assert from 'node:assert/strict';
import {buildProfile,inspectContainer,validateOptions} from './np3_tool.mjs';

const base=buildProfile({name:'LAB_TEST',options:{}});
assert.equal(base.binary.length,392);
assert.equal(base.decoded.saturation,0);
for(const options of [{saturation:101},{saturation:NaN},{sharpning:.1},
  {wrongField:0},{colorBlender:{blue:{hue:1000}}},{colorBlender:{infrared:{hue:0}}},
  {colorGrading:{blending:-1}},{identityToneCurve:false}])
  assert.throws(()=>validateOptions(options));
assert.throws(()=>buildProfile({name:'名字',options:{}}));
const curve=buildProfile({name:'CURVE_ID',options:{identityToneCurve:true}});
assert.equal(curve.decoded.toneCurve.raw.length,257);
assert.equal(curve.decoded.toneCurve.raw[0],0);
assert.equal(curve.decoded.toneCurve.raw[256],32767);
const corrupt=Buffer.from(base.binary);
corrupt.writeUInt32BE(0xffffffff,20);
assert.throws(()=>inspectContainer(corrupt));
const modified=buildProfile({name:'LAB_TEST',options:{colorBlender:{blue:{hue:20}}}});
const changed=[...base.binary.keys()].filter(i=>base.binary[i]!==modified.binary[i]);
assert.equal(changed.length,1,'Single blue-hue change must alter exactly one byte');
console.log(JSON.stringify({base_bytes:base.binary.length,curve_bytes:curve.binary.length,
  blue_hue_changed_byte:changed[0],strict_input_and_corruption_checks:'passed'},null,2));
