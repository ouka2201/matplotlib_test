import { NavItem } from "~/types";

export const navItems: NavItem[] = [
  {
    title: "cmtp01",
    name: "お知らせ",
    link: "/common/cmtp01",
    authorityId: "AB",
    groupId:"01",
    alwaysShow: true
  },
  {
    title: "ebdl01",
    name: "各種フォーマット出力",
    link: "/energy-building/ebdl01",
    authorityId: "A1",
    groupId:"01",
    alwaysShow: true
  },
  {
    title: "ebmg01",
    name: "レポート作成・管理",
    link: "/energy-building/ebmg01",
    authorityId: "A8",
    groupId:"02",
    alwaysShow: true
  },
  {
    title: "ebdl02",
    name: "CO2排出量集計",
    link: "/energy-building/ebdl02",
    authorityId: "C2",
    groupId:"02",
    alwaysShow: true
  },
  {
    title: "cmhp01",
    name: "マニュアル・同意書",
    link: "/common/cmhp01",
    authorityId: "A7",
    groupId:"01",
    alwaysShow: true
  },
  {
    title: "msog01",
    name: "利用組織マスタ登録・管理",
    link: "/master/msog01",
    authorityId: "D1",
    groupId:"04",
    alwaysShow: true
  },
  {
    title: "msus01",
    name: "ユーザー登録・管理",
    link: "/master/msus01",
    authorityId: "C1",
    groupId:"05",
    alwaysShow: true
  },
  {
    title: "mscs01",
    name: "お客さまマスタ登録・管理",
    link: "/master/mscs01",
    authorityId: "B1",
    groupId:"04",
    alwaysShow: true
  },
  {
    title: "msmg01",
    name: "営業担当登録・管理",
    link: "/master/msmg01",
    authorityId: "C3",
    groupId:"05",
    alwaysShow: true
  },
  {
    title: "ebmv01",
    name: "電力30分値登録",
    link: "/energy-building/ebmv01",
    authorityId: "B5",
    groupId:"03",
    alwaysShow: true
  },
  {
    title: "cmdl01",
    name: "データダウンロード",
    link: "/common/cmdl01",
    authorityId: "B6",
    groupId:"01",
    alwaysShow: true
  },
  {
    title: "cmcl01",
    name: "解約管理",
    link: "/common/cmcl01",
    authorityId: "D5",
    groupId:"02",
    alwaysShow: true
  },
];
