import { build } from 'esbuild';
await build({
  entryPoints: ['frontend/assistant.tsx'],
  outfile: 'evidence/static/evidence/ui.js',
  bundle: true,
  minify: true,
  format: 'iife',
  jsx: 'automatic',
  target: ['es2020'],
  define: {'process.env.NODE_ENV': JSON.stringify('production')},
  legalComments: 'eof',
});
