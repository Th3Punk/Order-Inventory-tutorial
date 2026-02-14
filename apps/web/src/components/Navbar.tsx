import { NavLink, useNavigate } from "react-router-dom";

import { api, setAccessToken } from "../lib/api";

const Navbar = () => {
  const navigate = useNavigate();

  const logout = async () => {
    try {
      await api.post("/auth/logout");
    } catch {
      // ignore network errors on logout
    }
    localStorage.removeItem("access_token");
    setAccessToken(null);
    navigate("/login");
  };

  return (
    <header className="navbar">
      <div className="brand">Orders Admin</div>
      <nav className="nav-links">
        <NavLink to="/orders">Orders</NavLink>
        <NavLink to="/orders/new">New order</NavLink>
        <NavLink to="/stats">Stats</NavLink>
      </nav>
      <button type="button" onClick={logout} className="logout-btn">
        Logout
      </button>
    </header>
  );
};

export default Navbar;
