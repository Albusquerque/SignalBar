import { rollup } from "rollup";
import config from "../rollup.config.js";

const configurations = Array.isArray(config) ? config : [config];

for (const current of configurations) {
  const bundle = await rollup(current);
  const outputs = Array.isArray(current.output) ? current.output : [current.output];
  for (const output of outputs) {
    await bundle.write(output);
  }
  await bundle.close();
}

// Some Rollup plugin versions keep a native worker handle alive on macOS even
// after close(). All output promises have settled, so ending here is safe and
// keeps `npm run build` deterministic on development hosts.
process.exit(0);

