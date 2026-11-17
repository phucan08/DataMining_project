import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
const runtimeRoot=process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES ?? 'C:/Users/GIGABYTE/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const require=createRequire(path.resolve(runtimeRoot,'../chart-renderer.cjs'));
const sharp=require('sharp');
const directory=path.resolve('results/figures');
const requested=process.argv[2];
const sources=(await fs.readdir(directory)).filter(name=>name.endsWith('.svg')&&(!requested||name===requested)).sort();
if(requested&&!sources.length)throw new Error('Requested SVG was not found in results/figures: '+requested);
for(const name of sources){
  await sharp(path.join(directory,name),{density:144}).png().toFile(path.join(directory,name.replace(/\.svg$/,'.png')));
}
process.stdout.write(JSON.stringify({rendered_pngs:sources.length})+'\n');
