import fs from 'node:fs/promises';
import {FileBlob,PresentationFile} from '@oai/artifact-tool';
const p=await PresentationFile.importPptx(await FileBlob.load('/Users/matiask/.codex/plugins/cache/openai-curated-remote/openai-templates/0.1.1/skills/artifact-template-simple-light-mode/assets/reference.pptx'));
console.log('collections',Object.getOwnPropertyNames(Object.getPrototypeOf(p.slides)));
console.log('slide',Object.getOwnPropertyNames(Object.getPrototypeOf(p.slides.items[3])));
console.log('shapes',Object.getOwnPropertyNames(Object.getPrototypeOf(p.slides.items[3].shapes)));
console.log((await p.inspect({kind:'slide,textbox',maxChars:5000})).ndjson);
await fs.writeFile('/Users/matiask/Documents/programacion/LIS/ghost_prompt/charla/.build/template.webp',new Uint8Array(await (await p.export({format:'webp',montage:true,scale:0.2})).arrayBuffer()));
await fs.writeFile('/Users/matiask/Documents/programacion/LIS/ghost_prompt/charla/.build/layout.json',await (await p.slides.items[3].export({format:'layout'})).text());
