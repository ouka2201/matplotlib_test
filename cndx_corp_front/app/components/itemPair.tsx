// import React from "react";
// import styles from "../styles/middleBase.module.css";
// import Text from "../components/text"

// type ItemPairProps = {
//   label: string;
//   content: string | React.ReactNode; // 入れ子対応
//   is80?: boolean; // true の場合は幅 80% にする
//   contentNoPadding?: boolean; // content部分にパディングなし
//   contentText?: string; // テキストをcontent内に追加
// };

// const ItemPair: React.FC<ItemPairProps> = ({
//   label,
//   content,
//   is80 = false,
//   contentNoPadding = false,
//   contentText,
// }) => {
//   return (
//     <div className={is80 ? styles.pair80 : styles.pairHorizontal}>
//       <div className={styles.labelBox}><Text content={label} color="gray-dark"/></div>
//       <div className={contentNoPadding ? styles.contentBoxNoPadding : styles.contentBox}>
//         {contentText && contentNoPadding && <div className={styles.contentBox}><Text content={contentText}/></div>}
//         {typeof content === "string" ? (
//           <div><Text content={content} color="gray-dark"/></div>
//         ) : (
//           content
//         )}
//       </div>
//     </div>
//   );
// };

// export default ItemPair;

import React from "react";
import styles from "../styles/middleBase.module.css";
import Text from "../components/text";

type ListItem = {
  label: string;
  content: string | React.ReactNode;
};

type ItemPairProps = {
  label?: string;
  // content は文字列／React要素、または ListItem の配列を受け付ける
  content: string | React.ReactNode | ListItem[];
  is80?: boolean; // true の場合は幅 80%
  contentNoPadding?: boolean;
  contentText?: string;
};

const ItemPair: React.FC<ItemPairProps> = ({
  label,
  content,
  is80 = false,
  contentNoPadding = false,
  contentText,
}) => {
  // content が配列の場合
  if (Array.isArray(content)) {
    // リストモード（label が渡されない場合）
    if (!label) {
      const columns = Math.min(content.length, 6);
      return (
        <div
          className={styles.listContainer}
          style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}
        >
          {content.map((item, index) => (
            <div key={index} className={styles.listItem}>
              <div className={styles.labelBoxList}>
                <Text content={item.label} color="gray-dark" />
              </div>
              <div className={styles.contentBoxList}>
                <Text content={item.content} />
              </div>
            </div>
          ))}
        </div>
      );
    } else {
      // label も渡されている場合：左側に label、右側にリストをグリッド表示
      const columns = Math.min(content.length, 6);
      return (
        <div className={styles.itemPairWithList}>
          <div className={styles.labelBox}>
            <Text content={label} color="gray-dark" />
          </div>
          <div
            className={styles.listContainer}
            style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}
          >
            {content.map((item, index) => (
              <div key={index} className={styles.listItem}>
                <div className={styles.labelBoxList}>
                  <Text content={item.label} color="gray-dark" />
                </div>
                <div className={styles.contentBoxList}>
                  <Text content={item.content} />
                </div>
              </div>
            ))}
          </div>
        </div>
      );
    }
  }

  // 通常のケース（content が文字列または React 要素の場合）
  return (
    <div className={is80 ? styles.pair80 : styles.pairHorizontal}>
      <div className={styles.labelBox}>
        <Text content={label!} color="gray-dark" />
      </div>
      <div className={contentNoPadding ? styles.contentBoxNoPadding : styles.contentBox}>
        {contentText && contentNoPadding && (
          <div className={styles.contentBox}>
            <Text content={contentText} />
          </div>
        )}
        {typeof content === "string" ? (
          <div>
            <Text content={content} color="gray-dark" />
          </div>
        ) : (
          content
        )}
      </div>
    </div>
  );
};

export default ItemPair;