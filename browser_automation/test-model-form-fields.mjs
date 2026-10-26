import test from 'node:test';
import assert from 'node:assert/strict';
import {fillModelFields} from './model-form-fields.mjs';

function fixture(){
 const job={role:'seed',platform_key:'doubao',selection:{field:'doubao-achievement-select',label:'未达成'},
   expected_base:{'question-input':'question','insight-input':'insight','insight-description-input':'point','non-decisive-insight-description-input':'无'},
   expected_selection:{domain:'生活娱乐',type:'openRecommendation'},
   text_fields:{'doubao-markdown-input':'**original**','doubao-achievement-note-input':'D1不满足'}};
 const elements=Object.fromEntries(Object.entries({...job.expected_base,...job.text_fields}).map(([id,value])=>[id,{value,tagName:'TEXTAREA',disabled:false,readOnly:false,maxLength:0}]));
 const selected={innerText:'未达成'};
 elements['doubao-achievement-select']={classList:{contains:()=>false},querySelector:()=>selected};
 const root={querySelector:s=>{
   if(s.includes('question-domain-select'))return {innerText:'生活娱乐'};
   if(s.includes('question-type-radio'))return {value:'openRecommendation'};
   if(s.includes('doubao-achievement-select')&&s.includes(' .ant-select-selection-item'))return selected;
   return elements[s.match(/data-field-id="([^"]+)"/)?.[1]];
 }};
 return {job,elements,selected,root};
}
test('same exact native fields are idempotent and never click or send',async()=>{
 const f=fixture(),result=await fillModelFields(f.root,f.job);
 assert.deepEqual(result.written,[]);assert.equal(result.submitted,false);
});
test('changed frozen base stops before any model text mutation',async()=>{
 const f=fixture();f.elements['question-input'].value='unrelated';f.elements['doubao-markdown-input'].value='';
 await assert.rejects(fillModelFields(f.root,f.job),/Native base differs/);
 assert.equal(f.elements['doubao-markdown-input'].value,'');
});
test('unknown reply or note is preserved before writing any other field',async()=>{
 const f=fixture();f.elements['doubao-markdown-input'].value='';f.elements['doubao-achievement-note-input'].value='private old note';
 await assert.rejects(fillModelFields(f.root,f.job),/Unrecognized existing/);
 assert.equal(f.elements['doubao-markdown-input'].value,'');
});
test('unrecorded attainment selection is preserved',async()=>{
 const f=fixture();f.selected.innerText='已达成';f.elements['doubao-markdown-input'].value='';
 await assert.rejects(fillModelFields(f.root,f.job),/Existing attainment differs/);
 assert.equal(f.elements['doubao-markdown-input'].value,'');
});
test('foreign role, arbitrary field, or missing input contract is blocked',async()=>{
 for(const mutate of [f=>f.job.role='arena_1',f=>f.job.text_fields['question-input']='bad',f=>delete f.job.expected_base['question-input']]){
   const f=fixture();mutate(f);await assert.rejects(fillModelFields(f.root,f.job),/contract|Unexpected/);
 }
});
