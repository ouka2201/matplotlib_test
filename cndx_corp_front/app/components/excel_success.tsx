import React, { useEffect, useState } from 'react';
import '../styles/middle-test2.css';
import { LoaderFunction } from '@remix-run/node';

export const loader: LoaderFunction = async ({ request }) => {
  const url = new URL(request.url);
  const filePath = url.searchParams.get("file");

  if (!filePath) {
    return new Response("File path is required", { status: 400 });
  }
};

const ExcelSuccess: React.FC = () => {
	const [fileName, setFileName] = useState<string | null>(null);

	useEffect(() => { // localStorage から fileName を取得
	const storedFileName = localStorage.getItem("fileName");
	if (storedFileName) {
		setFileName(storedFileName);
	}
	}, []);
  return (
    <div className="frame-top-body-excelupload">
      <div className="top-body-title-1e">
        <span className="top-body-title-text">Excelデータの登録を受け付けました。</span>
      </div>
    
      <div className="excelupload-content">
        <div className="excelupload-content-title">
          <span className="excelupload-content-title-text">
            選択されたファイル
          </span>
        </div>
        <div className="excelupload-content-fileinfo">
          <div className="excelupload-content-fileinfo-label">
            <div className="excelupload-content-fileinfo-label-text" />
			ファイル名
          </div>
          <div className="excelupload-content-fileinfo-name">
            <input className="excelupload-content-fileinfo-name_input" />
                    {/* ファイル名をボックス内に表示 */}
                    {fileName && (
                      <div >{/*ここはCSSを調整してBOXにいれる*/}
                      <span>{fileName}</span> {/* ファイル名を表示 */}
                      </div>
                    )} 
          </div>
        </div>
        <ul className="text-sm pt-2">
          <li className="text-gray-500">・２分程度で「CNレポート作成・検索」画面に対象のデータが表示されます。</li>
          <div className="text-red-500">※５分以上経過しても表示されない場合は、お手数ですがシステム管理者へお問い合わせください。</div>
        </ul>
      </div>
    </div>
  );
};

export default ExcelSuccess;
