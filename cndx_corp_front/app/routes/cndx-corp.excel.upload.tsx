import ExcelUpload from '~/pages/excelUpload';
import main_styles from '../styles/main.module.css';
// import type { MetaFunction } from "@remix-run/node";

// export const meta: MetaFunction = () => {
//   return [
//     { title: "入力シートアップロード" },
//     { name: "description", content: "upload Home" },
//   ];
// };

export default function InputSheetUpload() {
  return (
    <>
      <div className={main_styles.div_class}>
        <ExcelUpload />
      </div>
    </>
  );
}