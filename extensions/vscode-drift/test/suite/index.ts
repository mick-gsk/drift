/**
 * Mocha test suite root — discovers and runs all *.test.js files under
 * this directory.
 */

import * as path from "node:path";
import Mocha from "mocha";
import { glob } from "glob";

export function run(): Promise<void> {
  const mocha = new Mocha({ ui: "tdd", color: true, timeout: 10_000 });
  const testsRoot = path.resolve(__dirname, ".");

  return new Promise((resolve, reject) => {
    glob("**/*.test.js", { cwd: testsRoot })
      .then((files) => {
        for (const f of files) {
          mocha.addFile(path.resolve(testsRoot, f));
        }
        try {
          mocha.run((failures) => {
            if (failures > 0) {
              reject(new Error(`${failures} test(s) failed.`));
            } else {
              resolve();
            }
          });
        } catch (err) {
          reject(err);
        }
      })
      .catch(reject);
  });
}
