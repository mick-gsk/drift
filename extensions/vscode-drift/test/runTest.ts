/**
 * Test entry point — spawns a VS Code test host and runs the Mocha suite.
 * Called via `npm test` → `node ./out/test/runTest.js`.
 */

import * as path from "node:path";
import { runTests } from "@vscode/test-electron";

async function main(): Promise<void> {
  // The folder containing package.json for the extension under test.
  const extensionDevelopmentPath = path.resolve(__dirname, "../../");

  // The path to the extension test suite.
  const extensionTestsPath = path.resolve(__dirname, "./suite/index");

  await runTests({ extensionDevelopmentPath, extensionTestsPath });
}

main().catch((err) => {
  console.error("Failed to run tests:", err);
  process.exitCode = 1;
});
