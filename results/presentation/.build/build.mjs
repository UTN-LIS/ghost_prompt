import fs from 'node:fs/promises';
import {FileBlob,PresentationFile} from '@oai/artifact-tool';
import {finalizePresentation,applyPresentationChartFont} from '/Users/matiask/.codex/plugins/cache/openai-primary-runtime/presentations/26.905.11957/skills/presentations/container_tools/artifact_tool_utils.mjs';
const root='/Users/matiask/Documents/programacion/LIS/ghost_prompt/charla';
const skill='/Users/matiask/.codex/plugins/cache/openai-primary-runtime/presentations/26.905.11957/skills/presentations';
const p=await PresentationFile.importPptx(await FileBlob.load('/Users/matiask/.codex/plugins/cache/openai-curated-remote/openai-templates/0.1.1/skills/artifact-template-simple-light-mode/assets/reference.pptx'));
const s1=p.slides.items[3];
for(const s of [...p.slides.items])if(s!==s1)s.delete();
const s2=s1.duplicate();
const font='Helvetica Neue';
function text(s,str,x,y,w,h,size=28,color='#000000',bold=false){const t=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});t.text=str;t.text.style={typeface:font,fontSize:size,color,bold,autoFit:'none',insets:{left:0,right:0,top:0,bottom:0}};return t;}
for(const [i,s] of [s1,s2].entries()){
 for(const sh of [...s.shapes.items]){
  const st=sh.text?.toString?.()??'';
  if(st==='One column layout'){sh.text=i===0?'¿Y si elegimos el segundo token?':'Recuperación en 20 problemas';sh.text.style={typeface:font,fontSize:48,color:'#000000',autoFit:'none'};}
  else if(st.trim()==='4'){sh.text=String(i+1);}
  else s.shapes.deleteById(sh.id);
 }
}
text(s1,'¿Y si elegimos el segundo token?',41,36,1198,80,48);
text(s2,'Recuperación en 20 problemas',41,36,1198,80,48);
const img=await fs.readFile('/Users/matiask/.codex/generated_images/01a07d4b-b39c-78b1-bf14-597d19e003e1/exec-33a413e8-f350-4ab2-b162-10cf7fc49e5d.png');
await fs.writeFile(root+'/.build/metodo-final.png',img);
s1.images.add({blob:img,contentType:'image/png',alt:'Esquema de una bifurcación de la generación: conservar el prefijo y elegir el segundo token',fit:'contain',position:{left:41,top:180,width:1198,height:420}});
text(s1,'Conservar el prefijo, cambiar una decisión, continuar.',41,126,1198,42,30);
text(s1,'Matías Adolfo Koroch',41,651,700,34,24);
text(s1,'Esquema del método',960,612,278,32,20,'#555555');
text(s2,'Generaciones inicialmente fallidas · Hasta 5 ramas completas por problema',41,127,1198,48,26);
const ch=s2.charts.add('bar',{position:{left:65,top:198,width:1120,height:325},categories:['Aleatorio','Semántico','Entropía','Margen'],series:[{name:'Problemas recuperados',values:[6,10,10,10],fill:'#3D8DFF'}],barOptions:{direction:'bar',grouping:'clustered'},hasLegend:false,dataLabels:{showValue:true,position:'outEnd',textStyle:{fontSize:26}},xAxis:{textStyle:{fontSize:24}},yAxis:{textStyle:{fontSize:24}}});
applyPresentationChartFont(ch,{fontFamily:font});
text(s2,'El selector semántico supera al azar en esta muestra,\npero empata con entropía y margen.',41,549,1198,80,30,'#00264F',true);
text(s2,'Tests base de HumanEval. Pendiente: HumanEval+ y costo total.',41,658,1120,30,21,'#555555');
s1.speakerNotes.textFrame.setText('Modelo: Qwen/Qwen2.5-Coder-7B-Instruct. Se conserva el prefijo, se fuerza top-2 en una posición y se continúa greedy. Lookahead de 12 tokens incluyendo la decisión forzada. El lookahead sirve para ordenar y no determina éxito. Imagen esquemática generada con la herramienta integrada de imágenes. Fuente: experiments-2.ipynb del usuario y pestaña Metodología de https://docs.google.com/spreadsheets/d/1M5npFrFTIBJVB8QdpX9CXVhdMSO4l4Apd48I37OHDeE/edit');
s2.speakerNotes.textFrame.setText('Fuente: pestañas Resumen, Presupuesto y Metodología de https://docs.google.com/spreadsheets/d/1M5npFrFTIBJVB8QdpX9CXVhdMSO4l4Apd48I37OHDeE/edit . Consulta 7 septiembre 2026. 20 problemas fallidos con baseline greedy. Con k=5: semántico 10/20, entropía 10/20, margen 10/20 y aleatorio 6/20. Resultado preliminar, no afirmación de significancia. Con k=1: semántico 5, entropía 8, margen 6, azar 4. No se ejecutó HumanEval+. Igual número de ramas no implica igual costo total. HumanEval/26 excluido por desarrollo.');
await(await PresentationFile.exportPptx(p)).save(root+'/.build/candidate.pptx');
await finalizePresentation({workspaceDir:root,candidatePath:root+'/.build/candidate.pptx',finalPath:root+'/output/charla-conferencia.pptx',pythonExecutable:'/Users/matiask/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3',integrityValidatorPath:skill+'/container_tools/inspect_presentation_package_integrity.py',layoutValidatorPath:skill+'/container_tools/inspect_presentation_layout_geometry.py',layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit'],explicitTotalSlideCount:2,materializeLiteralChartWorkbooks:true,requiredNativeChartOwnerSlides:[2],fontPolicy:{basis:'design',families:[font]},verifyArtifactToolImport:true,receiptPath:root+'/.build/validation-v3.json'});
for(let i=0;i<2;i++)await fs.writeFile(root+`/.build/slide-${i+1}.png`,new Uint8Array(await(await p.slides.items[i].export({format:'png',scale:1})).arrayBuffer()));
console.log('DONE');
