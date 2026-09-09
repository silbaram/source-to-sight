/* Development-only structural guard. Runtime HTML does not depend on Acorn. */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {parse} = require(process.argv[2] || 'acorn');

function walk(node, visit) {
  if(!node || typeof node !== 'object')return;
  if(typeof node.type === 'string')visit(node);
  for(const value of Object.values(node)) {
    if(Array.isArray(value))value.forEach(child=>walk(child,visit));
    else if(value && typeof value === 'object')walk(value,visit);
  }
}

function check(script, template) {
  // Formatting is a separate guard: a same-line declaration is valid JS, so
  // node --check alone cannot enforce this repository's insertion convention.
  assert(!/\}[^\S\r\n]+function\s/m.test(script),'Separate closing braces and function declarations onto distinct lines');
  const ast=parse(script,{ecmaVersion:2022});
  assert.equal(ast.body.length,1,'Viewer must have one outer IIFE');
  const expression=ast.body[0].expression;
  assert.equal(expression?.type,'CallExpression');
  assert.equal(expression.callee.type,'ArrowFunctionExpression');
  assert.equal(expression.callee.body.type,'BlockStatement');
  const body=expression.callee.body.body;
  const required=['renderEntryFlow','renderCautions','renderGaps','renderEntrySummary','renderPalette','renderEntryContext','initializeEntry','initialize'];
  for(const name of required) {
    const declarations=[];
    walk(ast,node=>{if(node.type==='FunctionDeclaration'&&node.id.name===name)declarations.push(node);});
    assert.equal(declarations.length,1,name+' must be declared once');
    assert(body.includes(declarations[0]),name+' must be at IIFE body scope, not nested or outside it');
  }
  const last=body.at(-1);
  assert.equal(last.type,'ExpressionStatement');
  assert.equal(last.expression.type,'CallExpression');
  assert.equal(last.expression.callee.name,'initialize','Initialization must be a direct final IIFE statement');
  const initializer=body.find(node=>node.type==='FunctionDeclaration'&&node.id.name==='initializeEntry');
  const ordered=required.slice(0,5);
  assert(ordered.every(name=>body.indexOf(body.find(node=>node.type==='FunctionDeclaration'&&node.id.name===name))<body.indexOf(initializer)),
    'Entry renderers precede initializeEntry');
  const calls=[];
  walk(initializer.body,node=>{if(node.type==='CallExpression'&&node.callee.type==='Identifier'&&ordered.includes(node.callee.name))calls.push(node.callee.name);});
  assert.deepEqual(calls,['renderEntrySummary','renderGaps','renderPalette'],'Initial entry renders overview only; flows and cautions belong to the selected context');

  const ids=[...template.matchAll(/\bid="([^"]+)"/g)].map(match=>match[1]);
  assert.equal(ids.length,new Set(ids).size,'Static HTML IDs must be unique');
  const available=new Set(ids);
  // showItem creates this heading only while the inspector is open.
  const dynamicIds=new Set(['panel-title']);
  for(const id of dynamicIds) {
    let assigned=false;
    walk(ast,node=>{
      if(node.type==='AssignmentExpression'&&node.left.type==='MemberExpression'&&node.left.property.name==='id'&&node.right.value===id)assigned=true;
    });
    assert(assigned,'Documented dynamic ID is no longer assigned: '+id);available.add(id);
  }
  const references=new Set();
  walk(ast,node=>{
    if(node.type==='CallExpression'&&node.callee.type==='Identifier'&&node.callee.name==='$'&&node.arguments[0]?.type==='Literal')references.add(node.arguments[0].value);
  });
  for(const id of references)assert(available.has(id),'Missing viewer DOM target: '+id);
  // Texts use $(id) dynamically; their literal keys need the same protection.
  walk(initializer.body,node=>{
    if(node.type==='VariableDeclarator'&&node.id.name==='texts') {
      for(const property of node.init.properties)assert(available.has(property.key.value),'Missing translated DOM target: '+property.key.value);
    }
  });
  return references.size;
}

const root=path.resolve(__dirname,'../skills/code-flow/templates');
const script=fs.readFileSync(path.join(root,'viewer.js'),'utf8');
const template=fs.readFileSync(path.join(root,'flow-viewer-template.html'),'utf8');
const count=check(script,template);
// Fault injection checks the guards themselves, including syntactically valid
// scope mistakes that bracket counting (strings, comments, regex) can miss.
assert.throws(()=>check(script.replace('  function renderGaps()', '  function wrapper() {\n  function renderGaps()').replace('  function renderPalette()', '  }\n  function renderPalette()'),template),/IIFE body scope/);
assert.throws(()=>check(script.replace('\n  function renderGaps()', '  function renderGaps()'),template),/distinct lines/);
assert.throws(()=>check(script,template.replace('id="entry-flow-steps"','id="renamed-flow-steps"')),/Missing viewer DOM target/);
assert.throws(()=>check(script,template.replace('id="entry-cautions-title"','id="renamed-cautions-title"')),/Missing translated DOM target/);
assert.throws(()=>check(script.replace('  initialize();\n})();','  if (true) { initialize(); }\n})();'),template),/ExpressionStatement/);
console.log('Viewer static checks passed: separate declarations, '+count+' literal DOM references, translated IDs and IIFE scope (with fault injection).');
