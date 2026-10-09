import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, auth } from "../api.js";

export default function AuthPage({ register = false }) {
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "", first_name: "", last_name: "", household_name: "", address: "" });
  const [error, setError] = useState("");
  const onChange = (key) => (event) => setForm({ ...form, [key]: event.target.value });
  const submit = async (event) => {
    event.preventDefault();
    setError("");
    try {
      auth.save(await api(register ? "/auth/register/" : "/auth/login/", {
        method: "POST",
        body: register ? form : { email: form.email, password: form.password },
      }));
      navigate("/");
    } catch (requestError) {
      setError(requestError.message);
    }
  };

  return <div className="auth"><h1>Aqua<span style={{ color: "var(--ocean)" }}>Track</span></h1>
    <p className="sub">Know your water use, catch leaks early, and see your bill before it arrives.</p>
    <form onSubmit={submit}>
      {register && <>
        <input placeholder="First name" value={form.first_name} onChange={onChange("first_name")} required />
        <input placeholder="Last name" value={form.last_name} onChange={onChange("last_name")} required />
        <input placeholder="Household name (e.g. Cailing Home)" value={form.household_name} onChange={onChange("household_name")} />
        <input placeholder="Address" value={form.address} onChange={onChange("address")} />
      </>}
      <input type="email" placeholder="Email" value={form.email} onChange={onChange("email")} required />
      <input type="password" placeholder="Password (8+ characters)" value={form.password} onChange={onChange("password")} required />
      {error && <div className="err" role="alert">{error}</div>}
      <button>{register ? "Create account" : "Log in"}</button>
    </form>
    <p>{register ? <a href="/login">Already registered? Log in</a> : <a href="/register">New here? Create an account</a>}</p>
  </div>;
}