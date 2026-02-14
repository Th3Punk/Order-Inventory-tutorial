import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate } from "react-router-dom";

import { api, setAccessToken } from "../lib/api";

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(1, "Password is required"),
});

type FormData = z.infer<typeof schema>;

const LoginPage = () => {
  const navigate = useNavigate();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const onSubmit = async (data: FormData) => {
    const res = await api.post("/auth/login", data);
    const token = res.data?.access_token as string | undefined;
    if (token) {
      localStorage.setItem("access_token", token);
      setAccessToken(token);
      navigate("/orders");
    }
  };

  return (
    <main className="page">
      <div className="card">
        <h1>Login</h1>
        <form onSubmit={handleSubmit(onSubmit)} className="form">
          <label>
            Email
            <input type="email" {...register("email")} />
            {errors.email ? <span className="error">{errors.email.message}</span> : null}
          </label>
          <label>
            Password
            <input type="password" {...register("password")} />
            {errors.password ? <span className="error">{errors.password.message}</span> : null}
          </label>
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </div>
    </main>
  );
};

export default LoginPage;
