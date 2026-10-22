import { Link } from "@remix-run/react";
import "../../styles/header.css";
import { UserNav } from "./user-nav";

export default function Header() {
  return (
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
  );
}
