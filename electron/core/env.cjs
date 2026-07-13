/** Environment variable loader — loads .env via dotenv before any other
 *  module reads process.env. Must be require()-d first in main.cjs. */

const path = require("node:path");
const dotenv = require("dotenv");

dotenv.config({ path: path.join(process.cwd(), ".env.local") });
