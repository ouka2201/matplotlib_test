import { Link } from "@remix-run/react";
import { UserNav } from "./user-nav";
import "../../styles/header.css";
import BreadCrumb, { BreadCrumbType } from "~/components/common/breadcrumb";

interface LayoutProps {
  breadcrumbItems?: BreadCrumbType[];
}
export default function HeaderWithB({ breadcrumbItems }: LayoutProps) {
  return (
    <div>
      <div className="header-frame">
        <div className="logo-wrapper">
          <Link to="/common/cmtp01" className="logo-link">
            <div className="logo">
              <div className="header-tepco-logo" />
            </div>
            <div className="logo">
              <div className="header-lecmoc-logo" />
            </div>
          </Link>
        </div>

        <div className="user-nav-wrapper">
          <UserNav />
        </div>
      </div>
      <div className="breadcrumbWithB__list">{breadcrumbItems && <BreadCrumb items={breadcrumbItems} />}</div>
    </div>
  );
}
