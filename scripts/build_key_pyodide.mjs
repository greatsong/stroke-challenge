// 뇌졸중 예측 챌린지 정답표를 실습실과 같은 계산 환경(Pyodide 0.29.3 · scikit-learn 1.7.0)에서 만든다.
// 컴퓨터의 scikit-learn(1.8 등)으로 만들면 깊은 트리 몇 칸이 실습실 결과와 달라
// 정상 기록이 「확인 필요」로 빠진다(2026-09-23 확인, 57칸). 정답표는 반드시 이 파일로 만든다.
//
// 준비: 아무 폴더에서 npm i pyodide@0.29.3 (stlite 1.4.0이 쓰는 판)
// 실행: NODE_PATH=<그 폴더>/node_modules node scripts/build_key_pyodide.mjs [stroke.csv]
import { createRequire } from "module";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const require = createRequire(process.env.NODE_PATH ? path.join(process.env.NODE_PATH, "x") : import.meta.url);
const { loadPyodide } = require("pyodide");
const 여기 = path.dirname(fileURLToPath(import.meta.url));
const 결과파일 = path.join(여기, "..", "key.js");
const 데이터 = process.argv[2]
  ? fs.readFileSync(process.argv[2])
  : Buffer.from(await (await fetch("https://raw.githubusercontent.com/greatsong/modudata/main/data/stroke.csv")).arrayBuffer());

const py = await loadPyodide();
await py.loadPackage(["pandas", "scikit-learn"]);
py.FS.writeFile("/stroke.csv", 데이터);
py.FS.mkdirTree("/work/scripts");
py.globals.set("__file__", "/work/scripts/build_key.py");
await py.runPythonAsync("import sys; sys.argv = ['build_key.py', '/stroke.csv']\n" +
                        fs.readFileSync(path.join(여기, "build_key.py"), "utf8"));
fs.writeFileSync(결과파일, py.FS.readFile("/work/key.js"));
console.log("Pyodide에서 만든 정답표를 옮겼습니다:", 결과파일);
