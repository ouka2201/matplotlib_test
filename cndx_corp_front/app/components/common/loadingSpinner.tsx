import "~/styles/loader.css";

export const LoadingSpinner = ({ className = "", height = "100vh" }) => (
  <div
    className={`loading-container ${className}`}
    style={{ height }}
  >
    <div className="loading-spinner"></div>
    <p className="loading-text">Loading...</p>
  </div>
);