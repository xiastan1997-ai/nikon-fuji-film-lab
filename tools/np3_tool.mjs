/** NP3 calibration builder using the pinned MIT upstream library. */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { serialize, deserialize } from '../third_party/nikon-flexible-color-picture-control/src/mod.ts';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const BASE = {sharpning:2, midRangeSharpning:1, clarity:0, contrast:0,
  highlights:0, shadows:0, whiteLevel:0, blackLevel:0, saturation:0};
const CHANNELS = ['red','orange','yellow','green','cyan','blue','purple','magenta'];
const sha = data => crypto.createHash('sha256').update(data).digest('hex');

function number(value, min, max, step=1) {
  if (!Number.isFinite(value) || value < min || value > max ||
      Math.abs(value / step - Math.round(value / step)) > 1e-8)
    throw new Error(`Invalid parameter ${value}; expected ${min}..${max}, step ${step}`);
}
function keys(object, allowed) {
  if (!object || typeof object !== 'object' || Array.isArray(object)) throw new Error('Expected parameter object');
  for (const key of Object.keys(object)) if (!allowed.includes(key)) throw new Error(`Unknown parameter: ${key}`);
}
export function validateOptions(options) {
  keys(options, [...Object.keys(BASE),'colorBlender','colorGrading','identityToneCurve']);
  for (const [k,v] of Object.entries(options)) {
    if (k === 'sharpning') number(v,-3,9,.25);
    else if (['midRangeSharpning','clarity'].includes(k)) number(v,-5,5,.25);
    else if (k in BASE) number(v,-100,100);
  }
  if (options.colorBlender) {
    keys(options.colorBlender, CHANNELS);
    for (const values of Object.values(options.colorBlender)) {
      keys(values,['hue','chroma','brightness']);
      for (const value of Object.values(values)) number(value,-100,100);
    }
  }
  if (options.colorGrading) {
    keys(options.colorGrading,['highlights','midTone','shadows','blending','balance']);
    for (const [k,values] of Object.entries(options.colorGrading)) {
      if (k==='blending') {number(values,0,100); continue;}
      if (k==='balance') {number(values,-100,100); continue;}
      keys(values,['hue','chroma','brightness']);
      for (const [field,value] of Object.entries(values)) number(value,field==='hue'?0:-100,field==='hue'?360:100);
    }
  }
  if (options.identityToneCurve !== undefined && options.identityToneCurve !== true)
    throw new Error('identityToneCurve must be true or omitted');
}
export function inspectContainer(bytes) {
  const b=Buffer.from(bytes);
  assert.ok(b.length >= 392,'NP3 shorter than base container');
  assert.equal(b.subarray(0,4).toString('hex'),'4e435000','Invalid NCP magic');
  assert.equal(b.readUInt32BE(4),256,'Unexpected NP3 version');
  assert.equal(b.readUInt32BE(8),4,'Unexpected format length');
  assert.equal(b.subarray(12,16).toString('ascii'),'0310','Expected Flexible Color format 0310');
  let offset=16;
  for(let id=2;id<=32;id++) {
    assert.ok(offset+8<=b.length,'Truncated entry header');
    assert.equal(b.readUInt32BE(offset),id<<8,`Unexpected base tag ${id}`);
    const length=b.readUInt32BE(offset+4);
    assert.ok(length>0 && offset+8+length<=b.length,'Invalid entry length');
    offset+=8+length;
  }
  assert.equal(offset,388,'Unexpected base-entry boundary');
  return {bytes:b.length, base_entries:31, format:'0310', sha256:sha(b),
    note:'Header and base entries checked; color behavior and camera import remain unverified'};
}
function subset(actual, expected) {
  for(const [k,v] of Object.entries(expected)) {
    if(v && typeof v==='object' && !Array.isArray(v)) subset(actual[k],v);
    else assert.deepEqual(actual[k],v,`Decoded parameter mismatch: ${k}`);
  }
}
export function buildProfile(profile) {
  if(!/^[A-Za-z0-9_-]{1,19}$/.test(profile.name)) throw new Error('Use 1..19 ASCII name characters');
  validateOptions(profile.options);
  const options={...BASE,...profile.options,name:profile.name};
  if(options.identityToneCurve) {
    delete options.identityToneCurve;
    options.toneCurve={raw:Array.from({length:257},(_,i)=>Math.round(i*32767/256)),
      points:[{x:0,y:0},{x:128,y:128},{x:255,y:255}]};
  }
  const binary=serialize(options);
  const structure=inspectContainer(binary);
  const decoded=deserialize(binary);
  subset(decoded,options);
  assert.deepEqual(Buffer.from(serialize(decoded)),Buffer.from(binary),'Binary round-trip differs');
  return {binary,decoded,structure};
}
function buildLab(out) {
  const config=JSON.parse(fs.readFileSync(path.join(ROOT,'configs/lab-calibration.json'),'utf8'));
  const card=path.join(out,'NIKON','CUSTOMPC');
  fs.mkdirSync(card,{recursive:true});
  const files=[];
  for(const [i,profile] of config.profiles.entries()) {
    const built=buildProfile(profile);
    const filename=`PICCON${String(i+1).padStart(2,'0')}.NP3`;
    const target=path.join(card,filename);
    if(fs.existsSync(target) && !fs.readFileSync(target).equals(Buffer.from(built.binary)))
      throw new Error(`Refusing to overwrite different file ${target}`);
    fs.writeFileSync(target,built.binary);
    files.push({file:`NIKON/CUSTOMPC/${filename}`,id:profile.id,...built.structure,decoded:built.decoded});
  }
  const manifest={purpose:config.purpose,firmware_target:config.firmware_target,
    validation:'binary_structure_and_parameter_roundtrip_only',camera_import_tested:false,
    upstream_commit:'ed0397fbf1e4d4f2bc11ab3070522c613667d359',files};
  fs.writeFileSync(path.join(out,'manifest.json'),JSON.stringify(manifest,null,2)+'\n');
  fs.writeFileSync(path.join(out,'README.txt'),
    'Z6III C 2.01 calibration candidates - not film simulations.\n'+
    'Copy NIKON/CUSTOMPC to a camera-formatted card; use the primary slot.\n'+
    'First import PICCON01 (LAB_NEUTRAL) and PICCON02 (LAB_SAT_P20) into unused custom slots.\n'+
    'Record whether each imports and shoots. Keep WB, exposure, SDR, and all other settings fixed.\n'+
    'Camera import and color behavior have NOT been tested. Preserve your existing profiles.\n');
  console.log(JSON.stringify({out,files:files.length,camera_import_tested:false},null,2));
}
const [command,arg]=process.argv.slice(2);
if(command==='build-lab') buildLab(path.resolve(arg||path.join(ROOT,'outputs/calibration-z6iii-c201')));
else if(command==='inspect' && arg) {
  const bytes=fs.readFileSync(arg);
  console.log(JSON.stringify({structure:inspectContainer(bytes),parameters:deserialize(bytes)},null,2));
} else if(process.argv[1] && path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  console.error('Usage: node --experimental-strip-types tools/np3_tool.mjs build-lab [out-dir]\n       node --experimental-strip-types tools/np3_tool.mjs inspect <file.NP3>');
  process.exitCode=1;
}
