import React from "react";
import { styles, Text,  Layout, ItemPair } from "../components/import";

const sampleList = [
  { label: "2024/01", content: "123456" },
  { label: "2024/02", content: "123456" },
  { label: "2024/03", content: "123456" },
  { label: "2024/04", content: "123456" },
  { label: "2024/05", content: "123456" },
  { label: "2024/06", content: "123456" },
  { label: "2024/07", content: "123456" },
  { label: "2024/08", content: "123456" },
  { label: "2024/09", content: "123456" },
  { label: "2024/10", content: "123456" },
  { label: "2024/11", content: "123456" },
  { label: "2024/12", content: "123456" },
];

const CNinfo: React.FC = () => {

	
	return (
		<div className={styles.whiteBox}>
			<Text content="工場" size="lg"  weight="bold"/>
			<Layout direction="column" gap={8}>
				<Text content="基本情報" size="md" color="gray-dark"/>
				<Layout direction="column">
					<Layout direction="row">
						<ItemPair label="ファイル名" content="abc.tsx"/>
						<ItemPair label="ファイル名" content="abc.tsx"/>
					</Layout>
					<ItemPair label="ファイル名" content="abc.tsx"/>
					<ItemPair label="ファイル名" content="abc.tsx"/>
					<ItemPair label="ファイル名" content="abc.tsx"/>
				</Layout>
			</Layout>

			<Layout direction="column" gap={8}>
				<Text content="電力情報" size="md" color="gray-dark"/>
				<Layout direction="column">
					<ItemPair label="ファイル名" content="abc.tsx"/>
					<Layout direction="row">
						<ItemPair label="ファイル名" content="abc.tsx"/>
						<ItemPair label="ファイル名" content="abc.tsx"/>
					</Layout>
					<Layout direction="row">
						<ItemPair label="ファイル名" content="abc.tsx"/>
						<ItemPair label="ファイル名" content="abc.tsx"/>
					</Layout>
				</Layout>
			</Layout>

			<Layout direction="column" gap={8}>
				<Text content="エネルギー使用量" size="md" color="gray-dark"/>
				<Layout direction="column">
					<ItemPair label="ファイル名" contentText="abc.tsx" contentNoPadding
						content={<ItemPair content={sampleList} />}
					/>
					<ItemPair label="ファイル名" contentText="abc.tsx" contentNoPadding
						content={<ItemPair content={sampleList} />}
					/>
					<ItemPair label="ファイル名" contentText="abc.tsx" contentNoPadding
						content={<ItemPair content={sampleList} />}
					/>
					<ItemPair label="ファイル名" contentText="abc.tsx" contentNoPadding
						content={<ItemPair content={sampleList} />}
					/>
				</Layout>
			</Layout>
		</div>
	);
};

export default CNinfo;