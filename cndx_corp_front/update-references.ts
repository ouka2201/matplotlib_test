import fs from "fs";
import path from "path";

const oldFolder = "/assets/";
const newFolder = "/images/";
const projectDir = "./app"; // Remix のソースコードディレクトリ

/**
 * 指定されたディレクトリ内のファイルを再帰的に検索し、参照を更新する
 * @param dir - 検索を開始するディレクトリのパス
 */
function replaceReferences(dir: string): void {
  const files = fs.readdirSync(dir);

  files.forEach((file) => {
    const fullPath = path.join(dir, file);

    // ディレクトリなら再帰的に処理
    if (fs.statSync(fullPath).isDirectory()) {
      replaceReferences(fullPath);
    } else if (fullPath.endsWith(".tsx") || fullPath.endsWith(".ts")) {
      // .tsx や .ts ファイルのみ処理
      const content = fs.readFileSync(fullPath, "utf8");
      const updatedContent = content.replace(new RegExp(oldFolder, "g"), newFolder);

      if (content !== updatedContent) {
        fs.writeFileSync(fullPath, updatedContent, "utf8");
        console.log(`Updated references in: ${fullPath}`);
      }
    }
  });
}

// 実行
replaceReferences(projectDir);
console.log("Reference updates complete.");
