window.TW.AuthScreen = function AuthScreen({ onAuthenticated }) {
  const { apiJson } = window.TW;
  const [mode, setMode] = React.useState("login");
  const [username, setUsername] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [error, setError] = React.useState("");
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const isRegister = mode === "register";

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      const user = await apiJson(isRegister ? "/api/auth/register" : "/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ username: username.trim(), password }),
      });
      await onAuthenticated(user);
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  function switchMode(nextMode) {
    setMode(nextMode);
    setError("");
  }

  return (
    <>
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex min-h-14 max-w-7xl items-center justify-center px-3 py-2.5">
          <h1 className="text-center text-xl font-extrabold leading-tight tracking-normal">TOEIC SW Writing Browser</h1>
        </div>
      </header>
      <main className="mx-auto flex min-h-[calc(100vh-57px)] max-w-md items-center px-4 py-8">
        <section className="w-full rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="mb-4 flex rounded-md border border-slate-200 bg-slate-50 p-1">
            <button
              className={`min-h-9 flex-1 rounded px-3 text-sm font-bold ${!isRegister ? "bg-white text-teal-700 shadow-sm" : "text-slate-500 hover:text-slate-900"}`}
              type="button"
              onClick={() => switchMode("login")}
            >
              Login
            </button>
            <button
              className={`min-h-9 flex-1 rounded px-3 text-sm font-bold ${isRegister ? "bg-white text-teal-700 shadow-sm" : "text-slate-500 hover:text-slate-900"}`}
              type="button"
              onClick={() => switchMode("register")}
            >
              Register
            </button>
          </div>

          <form className="space-y-3" onSubmit={handleSubmit}>
            <label className="block text-sm font-semibold text-slate-700">
              Username
              <input
                className="mt-1 w-full rounded-md border border-slate-200 px-3 py-2 font-sans text-slate-900 focus:border-teal-700 focus:outline-none focus:ring-2 focus:ring-teal-50"
                autoComplete="username"
                pattern="[A-Za-z0-9_.-]{3,32}"
                required
                value={username}
                onChange={(event) => setUsername(event.target.value)}
              />
            </label>
            <label className="block text-sm font-semibold text-slate-700">
              Password
              <input
                className="mt-1 w-full rounded-md border border-slate-200 px-3 py-2 font-sans text-slate-900 focus:border-teal-700 focus:outline-none focus:ring-2 focus:ring-teal-50"
                autoComplete={isRegister ? "new-password" : "current-password"}
                minLength="6"
                required
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </label>

            {error ? <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</div> : null}

            <button
              className="min-h-10 w-full rounded-md border border-teal-700 bg-teal-700 px-3 py-2 text-sm font-bold text-white hover:bg-teal-800 disabled:cursor-wait disabled:opacity-70"
              disabled={isSubmitting}
              type="submit"
            >
              {isSubmitting ? "Working..." : isRegister ? "Create account" : "Login"}
            </button>
          </form>
        </section>
      </main>
    </>
  );
};
