import React from "react";

interface TextProps {
  content?: string;
  size?: string;
  color?: string;
  weight?: string;
  href?: string;
  children?: React.ReactNode;
  width?: string;
}

const Text: React.FC<TextProps> = ({
  content,
  size = 'base',
  color = 'black',
  weight = 'normal',
  href, //リンク用のプロパティ
  children,
  width,
}) => {
  const fontSize = `var(--font-size-${size})`;
  const fontColor = `var(--color-${color})`;
  const fontWeight = `var(--font-weight-${weight})`;

  const style = {
    fontFamily: 'Noto_Sans_JP',
    fontSize: fontSize,
    color: fontColor,
    fontWeight: fontWeight,
    textDecoration: href ? `underline` : 'none', //リンクなら下線をつける
    textDecorationColor: fontColor, //下線の色をテキストの色と同じにする
    textUnderlineOffset: "3px", //下線とテキストの距離
    cursor: href ? 'pointer' : 'default',
    width: width
  };

  return href ? (
    <a
      href={href}
      style={style}
      target="_blank"
      rel="noopener noreferrer"
    >
      {content || children}
    </a>
  ) : (
    <span style={style}>
      {content || children}
    </span>
  );
};

export default Text;


