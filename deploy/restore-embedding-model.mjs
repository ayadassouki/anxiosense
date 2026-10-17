// Restores the exact FastEmbed model used in the AnxioSense experiments
// (fast-bge-small-en-v1.5, the 2023-10-16 Qdrant GCS release) into the cache
// directory @mastra/fastembed reads: ~/.cache/mastra/fastembed-models.
//
// Why: @mastra/fastembed downloads this model only from
// storage.googleapis.com/qdrant-fastembed, which now returns HTTP 403, and the
// Hugging Face copy (Qdrant/bge-small-en-v1.5-onnx-Q) is a different, quantized
// model. Shipping the cached files keeps retrieval identical to the experiments.
//
// Every file is checked against its sha256; on any mismatch this exits non-zero
// so the server never starts with a different embedding model.
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const SRC = path.join(path.dirname(fileURLToPath(import.meta.url)), 'fastembed-models', 'fast-bge-small-en-v1.5');
const DEST = path.join(os.homedir(), '.cache', 'mastra', 'fastembed-models', 'fast-bge-small-en-v1.5');

const EXPECTED = {
  'config.json': 'cf423cc7d3c3202d0fecc4ca622fd996678c0b5a8abd56ba014413b8b4265639',
  'model_optimized.onnx': '20e3bd678b8e67a722f151f3ee1e3827fc3f230839c0d57c025a3753cefa6b2e',
  'ort_config.json': '97e78d1d21c2eb719e865b018f17915df6a12ed987446eb7f3f3a783a5afb1e1',
  'special_tokens_map.json': 'b6d346be366a7d1d48332dbc9fdf3bf8960b5d879522b7799ddba59e76237ee3',
  'tokenizer.json': 'd241a60d5e8f04cc1b2b3e9ef7a4921b27bf526d9f6050ab90f9267a1f9e5c66',
  'tokenizer_config.json': 'e1790949631401af1bfb6c9c7aeec7fcf612e274d73579d99f704faea40c8ba7',
  'vocab.txt': '07eced375cec144d27c900241f3e339478dec958f92fddbc551f295c992038a3',
};

const sha256 = (file) => createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const allValid = () => Object.entries(EXPECTED).every(([f, h]) => fs.existsSync(path.join(DEST, f)) && sha256(path.join(DEST, f)) === h);

if (allValid()) {
  console.log(`[embedding-model] verified in cache: ${DEST}`);
  process.exit(0);
}

fs.mkdirSync(DEST, { recursive: true });
for (const f of Object.keys(EXPECTED)) {
  if (f === 'model_optimized.onnx') {
    // Stored as split parts (GitHub's 100 MB per-file limit); concatenate in order.
    const parts = fs.readdirSync(SRC).filter((p) => p.startsWith('model_optimized.onnx.part-')).sort();
    if (parts.length === 0) throw new Error('model_optimized.onnx parts missing');
    fs.writeFileSync(path.join(DEST, f), Buffer.concat(parts.map((p) => fs.readFileSync(path.join(SRC, p)))));
  } else {
    fs.copyFileSync(path.join(SRC, f), path.join(DEST, f));
  }
}

const bad = Object.entries(EXPECTED).filter(([f, h]) => sha256(path.join(DEST, f)) !== h).map(([f]) => f);
if (bad.length) {
  console.error(`[embedding-model] sha256 mismatch: ${bad.join(', ')} - refusing to start`);
  process.exit(1);
}
console.log(`[embedding-model] restored and verified (7 files) in ${DEST}`);
